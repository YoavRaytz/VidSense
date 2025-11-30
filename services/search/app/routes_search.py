# backend/app/routes_search.py
"""
Search and RAG (Retrieval-Augmented Generation) routes.
Provides semantic search over video transcripts and AI-generated answers with citations.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from .db import get_db
from .embeddings import embed_text, combine_text_for_embedding
from .reranker import rerank
from .models import Video, Transcript, RetrievalFeedback, Collection
from .transcribe.gemini_client import GeminiTranscriber

router = APIRouter(prefix="/search", tags=["search"])


# ========== Schemas ==========

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    k: int = Field(default=10, ge=1, le=100, description="Number of final results to return")
    k_ann: int = Field(default=50, ge=1, le=200, description="Number of candidates for ANN search (before reranking)")


class SearchHit(BaseModel):
    video_id: str
    title: str | None
    author: str | None
    url: str
    score: float = Field(description="Similarity score (0-1, higher is better)")
    snippet: str = Field(description="Relevant text snippet from transcript")
    media_path: str | None = None
    source: str | None = None
    description: str | None = None


class SearchResponse(BaseModel):
    query: str
    hits: List[SearchHit]
    total: int


class RAGRequest(BaseModel):
    query: str = Field(..., description="Question to answer")
    k_ann: int = Field(default=20, ge=1, le=100, description="Number of candidates to retrieve")
    k_final: int = Field(default=5, ge=1, le=20, description="Number of sources to use in final answer")
    similar_collection_ids: List[str] = Field(default=[], description="IDs of similar collections to pull feedback from")


class RAGSource(BaseModel):
    video_id: str
    title: str | None
    author: str | None
    url: str
    snippet: str
    score: float
    source_type: str = Field(default="search", description="'search', 'collection', or 'feedback'")
    source_reference: str | None = Field(default=None, description="Reference to collection query or feedback source")


class ExcludedVideo(BaseModel):
    video_id: str
    title: str | None
    reason: str = Field(description="'liked_in_collection', 'disliked_in_collection', or 'bad_feedback'")
    source_reference: str | None = Field(default=None, description="Reference to collection or feedback source")


class RAGResponse(BaseModel):
    query: str
    answer: str = Field(description="AI-generated answer with inline citations")
    sources: List[RAGSource] = Field(description="Source videos used to generate the answer")
    excluded_videos: List[ExcludedVideo] = Field(default=[], description="Videos excluded from search (liked/disliked in collections)")


# ========== Search Endpoint ==========

@router.post("/query", response_model=SearchResponse)
def search_videos(payload: SearchRequest, db: Session = Depends(get_db)):
    """
    Two-stage semantic search: ANN retrieval → Cross-encoder reranking
    
    Process:
    1. Stage 1 (ANN): Embed query and retrieve k_ann candidates using pgvector
    2. Stage 2 (Rerank): Use cross-encoder to precisely rerank candidates
    3. Return top-k final results with snippets
    """
    print(f"[search] ========== NEW SEARCH ==========")
    print(f"[search] Query: '{payload.query}'")
    print(f"[search] k_ann={payload.k_ann}, k_final={payload.k}")
    
    if not payload.query.strip():
        return SearchResponse(query=payload.query, hits=[], total=0)
    
    # Stage 1: Generate query embedding
    try:
        print(f"[search] Stage 1: Generating query embedding...")
        query_embedding = embed_text(payload.query)
        print(f"[search] Embedding generated successfully")
    except Exception as e:
        print(f"[search][ERROR] Embedding failed: {e}")
        raise HTTPException(500, f"Failed to generate query embedding: {e}")
    
    # Stage 1: ANN search using pgvector (retrieve k_ann candidates)
    print(f"[search] Stage 1: Performing ANN search for {payload.k_ann} candidates...")
    sql = sql_text("""
        SELECT 
            t.video_id,
            v.title,
            v.author,
            v.url,
            v.source,
            v.description,
            v.media_path,
            t.text,
            (t.embedding <=> :query_vec) AS ann_distance,
            1 - (t.embedding <=> :query_vec) AS similarity_score
        FROM transcripts t
        JOIN videos v ON t.video_id = v.id
        WHERE t.embedding IS NOT NULL
        ORDER BY t.embedding <=> :query_vec
        LIMIT :limit
    """)
    
    try:
        # Optional: Set HNSW search parameter for better recall
        try:
            db.execute(sql_text("SET hnsw.ef_search = 80"))
        except:
            pass  # Ignore if HNSW not configured
        
        result = db.execute(
            sql,
            {"query_vec": json.dumps(query_embedding), "limit": payload.k_ann}
        ).fetchall()
    except Exception as e:
        print(f"[search][ERROR] Database query failed: {e}")
        raise HTTPException(500, f"Database search failed: {e}")
    
    print(f"[search] Stage 1: Retrieved {len(result)} candidates from ANN search")
    
    if not result:
        print(f"[search] No results found")
        return SearchResponse(query=payload.query, hits=[], total=0)
    
    # Convert to documents for reranking
    docs = []
    for row in result:
        video_id, title, author, url, source, description, media_path, text, ann_dist, sim_score = row
        
        # Combine title, description, and transcript for better reranking
        combined_text = ""
        if title:
            combined_text += f"Title: {title}\n\n"
        if description:
            combined_text += f"Description: {description}\n\n"
        if text:
            combined_text += f"Transcript: {text}"
        
        docs.append({
            "video_id": video_id,
            "title": title,
            "author": author,
            "url": url,
            "source": source,
            "description": description,
            "media_path": media_path,
            "text": combined_text,  # Use combined text for reranking
            "transcript_only": text or "",  # Keep original transcript for snippets
            "ann_distance": float(ann_dist),
            "vector_similarity": float(sim_score)
        })
    
    # Stage 2: Cross-Encoder Reranking
    print(f"[search] Stage 2: Cross-encoder reranking...")
    ranked_docs = rerank(payload.query, docs, text_key="text")
    print(f"[search] Stage 2: Reranking complete")
    
    # Apply softmax to scores for better distribution
    if ranked_docs:
        import math
        raw_scores = [d.get("rerank_score", 0.0) for d in ranked_docs]
        
        print(f"[search] Applying softmax to scores: raw range [{min(raw_scores):.4f}, {max(raw_scores):.4f}]")
        
        # Softmax: exp(score) / sum(exp(all_scores))
        exp_scores = [math.exp(s) for s in raw_scores]
        sum_exp = sum(exp_scores)
        
        for doc, exp_score in zip(ranked_docs, exp_scores):
            raw_score = doc.get("rerank_score", 0.0)
            softmax_score = exp_score / sum_exp
            doc["rerank_score"] = softmax_score
            print(f"[search]   video_id={doc['video_id'][:16]}: raw={raw_score:.4f} -> softmax={softmax_score:.4f} ({softmax_score*100:.1f}%)")
    
    # Convert to SearchHit objects and take top-k
    hits = []
    for i, doc in enumerate(ranked_docs[:payload.k], 1):
        # Use transcript_only for snippet generation (not the combined text)
        snippet = _generate_snippet(doc.get("transcript_only", ""), payload.query, max_length=200)
        rerank_score = doc.get("rerank_score", 0.0)
        
        title = doc.get('title') or 'Untitled'
        title_display = title[:40] if len(title) > 40 else title
        
        print(f"[search] Result #{i}: video_id={doc['video_id'][:16]}..., rerank_score={rerank_score:.4f}, title={title_display}")
        
        hits.append(SearchHit(
            video_id=doc["video_id"],
            title=doc["title"],
            author=doc["author"],
            url=doc["url"],
            source=doc["source"],
            description=doc["description"],
            media_path=doc["media_path"],
            score=rerank_score,  # Use rerank score as the final score
            snippet=snippet
        ))
    
    print(f"[search] Returning {len(hits)} final results")
    print(f"[search] ========== SEARCH COMPLETE ==========\n")
    
    return SearchResponse(
        query=payload.query,
        hits=hits,
        total=len(result)
    )


# ========== RAG Endpoint ==========

@router.post("/rag", response_model=RAGResponse)
def rag_answer(payload: RAGRequest, db: Session = Depends(get_db)):
    """
    Retrieval-Augmented Generation: Answer questions using video transcripts.
    
    Enhanced with collection feedback:
    1. Pull liked videos from similar collections automatically
    2. Exclude both liked and disliked videos from new searches (optimization)
    3. Mark sources with their origin (search/collection/feedback)
    4. Track excluded videos for transparency
    5. Generate answer with Gemini using combined sources
    """
    print(f"[rag] ========== NEW RAG REQUEST ==========")
    print(f"[rag] Query: '{payload.query}'")
    print(f"[rag] k_ann={payload.k_ann}, k_final={payload.k_final}")
    print(f"[rag] Similar collections: {len(payload.similar_collection_ids)}")
    
    if not payload.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    
    # Step 0: Embed query for feedback search
    query_embedding = embed_text(payload.query)
    
    # Step 1: Process similar collections to get liked/disliked videos
    liked_from_collections = {}  # video_id -> collection_query
    disliked_from_collections = {}  # video_id -> collection_query
    excluded_videos_list = []
    
    if payload.similar_collection_ids:
        print(f"[rag] Step 1: Processing {len(payload.similar_collection_ids)} similar collections for feedback...")
        
        for collection_id in payload.similar_collection_ids:
            collection = db.get(Collection, collection_id)
            if not collection:
                continue
            
            collection_query = collection.query
            print(f"[rag]   Collection: '{collection_query}'")
            
            # Get all feedback for this collection's query
            feedback_records = db.query(RetrievalFeedback).filter(
                RetrievalFeedback.query == collection_query
            ).all()
            
            for fb in feedback_records:
                video_id = fb.video_id
                feedback_type = fb.feedback
                
                if feedback_type == 'good':
                    liked_from_collections[video_id] = collection_query
                    print(f"[rag]     ✓ Liked: {video_id[:16]}...")
                elif feedback_type == 'bad':
                    disliked_from_collections[video_id] = collection_query
                    print(f"[rag]     ✗ Disliked: {video_id[:16]}...")
    
    # Step 2: Also get feedback from similar queries (original logic)
    print(f"[rag] Step 2: Finding similar past queries...")
    similar_queries_result = find_similar_queries(
        SearchRequest(query=payload.query, k=payload.k_final, k_ann=payload.k_ann),
        db
    )
    
    liked_from_queries = set()
    disliked_from_queries = set()
    
    for sim_query in similar_queries_result.similar_queries:
        print(f"[rag]   Similar query: '{sim_query.query}' (similarity={sim_query.similarity:.4f})")
        liked_from_queries.update(sim_query.good_video_ids)
        disliked_from_queries.update(sim_query.bad_video_ids)
    
    # Combine all exclusions (optimization: don't search for videos we already know about)
    exclude_video_ids = (
        set(liked_from_collections.keys()) | 
        set(disliked_from_collections.keys()) |
        liked_from_queries |
        disliked_from_queries
    )
    
    print(f"[rag] Total exclusions from search: {len(exclude_video_ids)}")
    print(f"[rag]   Liked from collections: {len(liked_from_collections)}")
    print(f"[rag]   Disliked from collections: {len(disliked_from_collections)}")
    print(f"[rag]   Liked from queries: {len(liked_from_queries)}")
    print(f"[rag]   Disliked from queries: {len(disliked_from_queries)}")
    
    # Build excluded videos list for response
    for video_id, collection_query in liked_from_collections.items():
        video = db.get(Video, video_id)
        excluded_videos_list.append(ExcludedVideo(
            video_id=video_id,
            title=video.title if video else None,
            reason="liked_in_collection",
            source_reference=collection_query
        ))
    
    for video_id, collection_query in disliked_from_collections.items():
        video = db.get(Video, video_id)
        excluded_videos_list.append(ExcludedVideo(
            video_id=video_id,
            title=video.title if video else None,
            reason="disliked_in_collection",
            source_reference=collection_query
        ))
    
    for video_id in disliked_from_queries:
        if video_id not in disliked_from_collections:  # Avoid duplicates
            video = db.get(Video, video_id)
            excluded_videos_list.append(ExcludedVideo(
                video_id=video_id,
                title=video.title if video else None,
                reason="bad_feedback",
                source_reference="similar_query"
            ))
    
    # Step 3: Perform new search (excluding already-known videos)
    print(f"[rag] Step 3: Performing search (excluding {len(exclude_video_ids)} videos)...")
    search_req = SearchRequest(query=payload.query, k=payload.k_final * 2, k_ann=payload.k_ann)
    search_result = search_videos(search_req, db)
    
    # Filter out excluded videos
    filtered_hits = [hit for hit in search_result.hits if hit.video_id not in exclude_video_ids]
    print(f"[rag]   Filtered to {len(filtered_hits)} new results (from {len(search_result.hits)} original)")
    
    # Step 4: Fetch liked videos from collections to include in context
    sources_from_collections = []
    for video_id, collection_query in liked_from_collections.items():
        video = db.get(Video, video_id)
        transcript = db.get(Transcript, video_id)
        if video and transcript:
            transcript_text = transcript.text or ''
            snippet = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
            sources_from_collections.append({
                'hit': SearchHit(
                    video_id=video.id,
                    title=video.title,
                    author=video.author,
                    url=video.url,
                    score=1.0,
                    snippet=snippet,
                    media_path=video.media_path,
                    source=video.source,
                    description=video.description
                ),
                'source_type': 'collection',
                'reference': collection_query
            })
    
    print(f"[rag]   Pulled {len(sources_from_collections)} liked videos from collections")
    
    # Step 5: Fetch liked videos from similar queries
    sources_from_queries = []
    for video_id in liked_from_queries:
        if video_id in liked_from_collections:
            continue  # Already included
        video = db.get(Video, video_id)
        transcript = db.get(Transcript, video_id)
        if video and transcript:
            transcript_text = transcript.text or ''
            snippet = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
            sources_from_queries.append({
                'hit': SearchHit(
                    video_id=video.id,
                    title=video.title,
                    author=video.author,
                    url=video.url,
                    score=1.0,
                    snippet=snippet,
                    media_path=video.media_path,
                    source=video.source,
                    description=video.description
                ),
                'source_type': 'feedback',
                'reference': 'similar_query'
            })
    
    print(f"[rag]   Pulled {len(sources_from_queries)} liked videos from queries")
    
    # Combine all sources: collection sources + query sources + new search results
    all_sources = []
    
    # Priority 1: Sources from collections (user explicitly liked in related searches)
    for src in sources_from_collections:
        all_sources.append(src)
    
    # Priority 2: Sources from queries (implicit positive feedback)
    for src in sources_from_queries:
        all_sources.append(src)
    
    # Priority 3: New search results
    for hit in filtered_hits:
        all_sources.append({
            'hit': hit,
            'source_type': 'search',
            'reference': None
        })
    
    # Take top k_final
    top_sources = all_sources[:payload.k_final]
    
    if not top_sources:
        print(f"[rag] No results found after filtering")
        return RAGResponse(
            query=payload.query,
            answer="I couldn't find any relevant information in the video database to answer your question.",
            sources=[],
            excluded_videos=excluded_videos_list
        )
    
    print(f"[rag] Using {len(top_sources)} sources for answer generation")
    print(f"[rag]   From collections: {len(sources_from_collections)}")
    print(f"[rag]   From queries: {len(sources_from_queries)}")
    print(f"[rag]   From new search: {len([s for s in top_sources if s['source_type'] == 'search'])}")
    
    # Step 6: Build context with numbered sources
    context_parts = []
    rag_sources = []
    
    for idx, src_data in enumerate(top_sources, 1):
        hit = src_data['hit']
        source_type = src_data['source_type']
        reference = src_data['reference']
        
        title = hit.title or 'Untitled'
        title_display = title[:40] if len(title) > 40 else title
        
        source_marker = ""
        if source_type == 'collection':
            source_marker = f" [from collection: '{reference}']"
        elif source_type == 'feedback':
            source_marker = " [from similar query feedback]"
        
        print(f"[rag] Source [{idx}]: video_id={hit.video_id[:16]}..., score={hit.score:.4f}, title={title_display}, type={source_type}{source_marker}")
        
        # Get full transcript
        transcript_obj = db.get(Transcript, hit.video_id)
        transcript_text = hit.snippet  # default (fallback if no transcript found)
        
        if transcript_obj:
            text_val = getattr(transcript_obj, 'text', None)
            if text_val is not None:
                transcript_text = str(text_val)
                print(f"[rag]   Using full transcript ({len(transcript_text)} chars)")
            else:
                print(f"[rag]   WARNING: Transcript object exists but has no text, using snippet ({len(transcript_text)} chars)")
        else:
            print(f"[rag]   WARNING: No transcript found for video {hit.video_id[:16]}..., using snippet ({len(transcript_text)} chars)")
        
        # Truncate very long transcripts
        original_len = len(transcript_text)
        if len(transcript_text) > 3000:
            transcript_text = transcript_text[:3000] + "..."
            print(f"[rag]   Truncated transcript from {original_len} to 3000 chars")
        
        context_parts.append(f"[Source {idx}] {hit.title or 'Untitled'}\n{transcript_text}\n")
        
        rag_sources.append(RAGSource(
            video_id=hit.video_id,
            title=hit.title,
            author=hit.author,
            url=hit.url,
            snippet=hit.snippet,
            score=hit.score,
            source_type=source_type,
            source_reference=reference
        ))
    
    context = "\n\n".join(context_parts)
    print(f"[rag] Built context with {len(context)} characters from {len(rag_sources)} sources")
    
    # Step 7: Generate answer with Gemini
    print(f"[rag] Generating answer with Gemini...")
    prompt = f"""You are a helpful assistant that answers questions based on video transcripts.

Question: {payload.query}

Context (from video transcripts):
{context}

Instructions:
- Answer the question using ONLY information from the provided sources
- Cite sources using inline references like [1], [2], etc.
- Be concise but informative
- If the sources don't contain enough information, say so
- Use natural language and proper formatting

Answer:"""
    
    try:
        # Use Gemini for generation (reuse existing client)
        import os
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(500, "GEMINI_API_KEY not set")
        
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        answer = getattr(response, "text", None) or "Failed to generate answer."
        print(f"[rag] Answer generated successfully ({len(answer)} chars)")
        
    except Exception as e:
        print(f"[rag][ERROR] Generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to generate answer: {e}")
    
    print(f"[rag] Returning answer with {len(rag_sources)} sources and {len(excluded_videos_list)} excluded videos")
    print(f"[rag] ========== RAG COMPLETE ==========\n")
    
    return RAGResponse(
        query=payload.query,
        answer=answer,
        sources=rag_sources,
        excluded_videos=excluded_videos_list
    )


# ========== Helper Functions ==========

def _generate_snippet(text: str, query: str, max_length: int = 200) -> str:
    """
    Extract a relevant snippet from text based on query terms.
    Tries to find text around query keywords.
    """
    if not text:
        return ""
    
    # Clean text
    text = text.strip()
    if len(text) <= max_length:
        return text
    
    # Try to find query terms
    query_terms = query.lower().split()
    text_lower = text.lower()
    
    # Find first occurrence of any query term
    best_pos = None
    for term in query_terms:
        if term in text_lower:
            pos = text_lower.find(term)
            if best_pos is None or pos < best_pos:
                best_pos = pos
    
    if best_pos is not None:
        # Extract window around the match
        start = max(0, best_pos - max_length // 2)
        end = min(len(text), start + max_length)
        
        # Adjust start if we're too close to the end
        if end - start < max_length:
            start = max(0, end - max_length)
        
        snippet = text[start:end]
        
        # Add ellipsis
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    # Fallback: just return beginning
    return text[:max_length] + "..."


def _rerank_results(query: str, hits: List[SearchHit], max_results: int = 10) -> List[SearchHit]:
    """
    Rerank search results using a more sophisticated scoring method.
    
    For now, we'll use a simple hybrid approach:
    - Keep vector similarity as primary signal
    - Boost results that have exact query term matches
    - Consider title matches highly
    
    In production, you might use a cross-encoder model here.
    """
    query_lower = query.lower()
    query_terms = set(query_lower.split())
    
    def compute_rerank_score(hit: SearchHit) -> float:
        base_score = hit.score
        boost = 0.0
        
        # Boost for title match
        if hit.title:
            title_lower = hit.title.lower()
            if query_lower in title_lower:
                boost += 0.2
            # Partial term matches
            title_terms = set(title_lower.split())
            overlap = len(query_terms & title_terms)
            boost += overlap * 0.05
        
        # Boost for exact phrase in snippet
        if query_lower in hit.snippet.lower():
            boost += 0.15
        
        return base_score + boost
    
    # Rerank
    scored_hits = [(compute_rerank_score(hit), hit) for hit in hits]
    scored_hits.sort(key=lambda x: x[0], reverse=True)
    
    return [hit for _, hit in scored_hits[:max_results]]


# ========== Retrieval Feedback Endpoints ==========

class FeedbackRequest(BaseModel):
    query: str = Field(..., description="The search query")
    video_id: str = Field(..., description="The video ID that was retrieved")
    feedback: str = Field(..., description="'good' or 'bad'")


class SimilarQuery(BaseModel):
    query: str
    similarity: float
    good_video_ids: List[str]
    bad_video_ids: List[str]


class SimilarQueriesResponse(BaseModel):
    query: str
    similar_queries: List[SimilarQuery]


@router.post("/feedback", status_code=201)
def save_retrieval_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Save feedback (good/bad) for a retrieved source.
    This helps the system learn which sources are relevant for specific queries.
    Updates existing feedback if the same query+video_id combination exists.
    """
    print(f"[feedback] Saving feedback: query='{payload.query}', video_id={payload.video_id}, feedback={payload.feedback}")
    
    if payload.feedback not in ['good', 'bad']:
        raise HTTPException(400, "Feedback must be 'good' or 'bad'")
    
    # Generate query embedding
    try:
        query_embedding = embed_text(payload.query)
    except Exception as e:
        print(f"[feedback][ERROR] Failed to generate query embedding: {e}")
        raise HTTPException(500, f"Failed to generate query embedding: {e}")
    
    # Check if feedback already exists for this query+video combination
    try:
        existing_feedback = db.query(RetrievalFeedback).filter(
            RetrievalFeedback.query == payload.query,
            RetrievalFeedback.video_id == payload.video_id
        ).first()
        
        if existing_feedback:
            # Update existing feedback
            print(f"[feedback] Updating existing feedback from '{existing_feedback.feedback}' to '{payload.feedback}'")
            existing_feedback.feedback = payload.feedback
            existing_feedback.query_embedding = query_embedding
        else:
            # Create new feedback
            print(f"[feedback] Creating new feedback record")
            feedback = RetrievalFeedback(
                query=payload.query,
                query_embedding=query_embedding,
                video_id=payload.video_id,
                feedback=payload.feedback
            )
            db.add(feedback)
        
        db.commit()
        print(f"[feedback] Feedback saved successfully")
        return {"status": "success", "message": "Feedback saved"}
    except Exception as e:
        db.rollback()
        print(f"[feedback][ERROR] Failed to save feedback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to save feedback: {e}")


class DeleteFeedbackRequest(BaseModel):
    query: str = Field(..., description="The search query")
    video_id: str = Field(..., description="Video ID to delete feedback for")


@router.delete("/feedback", status_code=200)
def delete_retrieval_feedback(payload: DeleteFeedbackRequest, db: Session = Depends(get_db)):
    """
    Delete feedback for a specific query+video combination.
    Used when user wants to unselect/remove their feedback.
    """
    print(f"[feedback-delete] Deleting feedback: query='{payload.query}', video_id={payload.video_id}")
    
    try:
        # Find and delete the feedback
        deleted_count = db.query(RetrievalFeedback).filter(
            RetrievalFeedback.query == payload.query,
            RetrievalFeedback.video_id == payload.video_id
        ).delete()
        
        db.commit()
        
        if deleted_count > 0:
            print(f"[feedback-delete] Successfully deleted {deleted_count} feedback record(s)")
            return {"status": "success", "message": "Feedback deleted", "deleted": deleted_count}
        else:
            print(f"[feedback-delete] No feedback found to delete")
            return {"status": "success", "message": "No feedback found", "deleted": 0}
    except Exception as e:
        db.rollback()
        print(f"[feedback-delete][ERROR] Failed to delete feedback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to delete feedback: {e}")


class GetFeedbackRequest(BaseModel):
    query: str = Field(..., description="The search query")
    video_ids: List[str] = Field(..., description="List of video IDs to get feedback for")


class VideoFeedback(BaseModel):
    video_id: str
    feedback: str  # 'good' or 'bad'


class GetFeedbackResponse(BaseModel):
    query: str
    feedback: List[VideoFeedback]


@router.post("/feedback/get", response_model=GetFeedbackResponse)
def get_retrieval_feedback(payload: GetFeedbackRequest, db: Session = Depends(get_db)):
    """
    Get existing feedback for specific videos and query.
    Returns list of video IDs with their feedback status.
    """
    print(f"[get-feedback] Getting feedback for query='{payload.query}', videos={len(payload.video_ids)}")
    
    if not payload.video_ids:
        return GetFeedbackResponse(query=payload.query, feedback=[])
    
    try:
        # Query feedback for this query and these video IDs
        sql = sql_text("""
            SELECT DISTINCT ON (video_id) video_id, feedback
            FROM retrieval_feedback
            WHERE query = :query
                AND video_id = ANY(:video_ids)
            ORDER BY video_id, created_at DESC
        """)
        
        result = db.execute(
            sql,
            {"query": payload.query, "video_ids": payload.video_ids}
        ).fetchall()
        
        feedback_list = [
            VideoFeedback(video_id=video_id, feedback=feedback)
            for video_id, feedback in result
        ]
        
        print(f"[get-feedback] Found {len(feedback_list)} feedback records")
        return GetFeedbackResponse(query=payload.query, feedback=feedback_list)
        
    except Exception as e:
        print(f"[get-feedback][ERROR] Failed to get feedback: {e}")
        raise HTTPException(500, f"Failed to get feedback: {e}")


@router.post("/similar-queries", response_model=SimilarQueriesResponse)
def find_similar_queries(payload: SearchRequest, db: Session = Depends(get_db)):
    """
    Find similar past queries based on semantic similarity.
    Returns queries with their good/bad source feedback.
    """
    print(f"[similar-queries] Finding similar queries for: '{payload.query}'")
    
    if not payload.query.strip():
        return SimilarQueriesResponse(query=payload.query, similar_queries=[])
    
    # Generate query embedding
    try:
        query_embedding = embed_text(payload.query)
    except Exception as e:
        print(f"[similar-queries][ERROR] Failed to generate query embedding: {e}")
        raise HTTPException(500, f"Failed to generate query embedding: {e}")
    
    # Find similar queries (similarity > 0.85 threshold)
    sql = sql_text("""
        SELECT DISTINCT
            query,
            1 - (query_embedding <=> :query_vec) AS similarity
        FROM retrieval_feedback
        WHERE query_embedding IS NOT NULL
            AND 1 - (query_embedding <=> :query_vec) > 0.85
        ORDER BY similarity DESC
        LIMIT 5
    """)
    
    try:
        result = db.execute(
            sql,
            {"query_vec": json.dumps(query_embedding)}
        ).fetchall()
    except Exception as e:
        print(f"[similar-queries][ERROR] Database query failed: {e}")
        raise HTTPException(500, f"Failed to find similar queries: {e}")
    
    print(f"[similar-queries] Found {len(result)} similar queries")
    
    similar_queries = []
    for row in result:
        query_text, similarity = row
        
        # Skip if it's the exact same query
        if query_text.strip().lower() == payload.query.strip().lower():
            continue
        
        # Get good and bad sources for this query
        feedback_sql = sql_text("""
            SELECT video_id, feedback
            FROM retrieval_feedback
            WHERE query = :query
        """)
        feedback_result = db.execute(feedback_sql, {"query": query_text}).fetchall()
        
        good_video_ids = [vid for vid, fb in feedback_result if fb == 'good']
        bad_video_ids = [vid for vid, fb in feedback_result if fb == 'bad']
        
        similar_queries.append(SimilarQuery(
            query=query_text,
            similarity=float(similarity),
            good_video_ids=good_video_ids,
            bad_video_ids=bad_video_ids
        ))
    
    return SimilarQueriesResponse(
        query=payload.query,
        similar_queries=similar_queries
    )


# ========== Similar Collections Endpoint ==========

class CollectionVideo(BaseModel):
    id: str
    title: str | None
    author: str | None
    url: str
    score: float | None = None
    snippet: str | None = None
    description: str | None = None
    clip_count: int | None = None
    hashtags: List[str] | None = None


class SimilarCollectionResult(BaseModel):
    id: str
    query: str
    similarity: float
    ai_answer: str | None
    videos: List[CollectionVideo]
    created_at: str
    metadata_json: dict = {}


class SimilarCollectionsResponse(BaseModel):
    query: str
    collections: List[SimilarCollectionResult]


@router.post("/similar-collections", response_model=SimilarCollectionsResponse)
def find_similar_collections(payload: SearchRequest, db: Session = Depends(get_db)):
    """
    Find similar past collections based on semantic similarity of queries.
    Returns full collection details including AI answers and source videos.
    Threshold: 70% similarity (0.50)
    """
    print(f"[similar-collections] Finding similar collections for: '{payload.query}'")
    
    if not payload.query.strip():
        return SimilarCollectionsResponse(query=payload.query, collections=[])
    
    # Generate query embedding
    try:
        query_embedding = embed_text(payload.query)
    except Exception as e:
        print(f"[similar-collections][ERROR] Failed to generate query embedding: {e}")
        raise HTTPException(500, f"Failed to generate query embedding: {e}")
    
    # Find similar collections (similarity > 0.50 threshold)
    sql = sql_text("""
        SELECT 
            id,
            query,
            ai_answer,
            video_ids,
            metadata_json,
            created_at,
            1 - (query_embedding <=> :query_vec) AS similarity
        FROM collections
        WHERE query_embedding IS NOT NULL
            AND 1 - (query_embedding <=> :query_vec) > 0.50
        ORDER BY similarity DESC
        LIMIT 10
    """)
    
    try:
        result = db.execute(
            sql,
            {"query_vec": json.dumps(query_embedding)}
        ).fetchall()
    except Exception as e:
        print(f"[similar-collections][ERROR] Database query failed: {e}")
        raise HTTPException(500, f"Failed to find similar collections: {e}")
    
    print(f"[similar-collections] Found {len(result)} similar collections")
    
    similar_collections = []
    for row in result:
        collection_id, query_text, ai_answer, video_ids, metadata_json, created_at, similarity = row
        
        # Skip if it's the exact same query
        if query_text.strip().lower() == payload.query.strip().lower():
            continue
        
        # Fetch video details for this collection
        videos_data = []
        if video_ids:
            videos = db.query(Video).filter(Video.id.in_(video_ids)).all()
            
            # Create a mapping to preserve order and include scores from metadata
            video_map = {v.id: v for v in videos}
            
            # Get scores from metadata if available
            scores_map = {}
            if metadata_json and 'source_scores' in metadata_json:
                scores_map = metadata_json['source_scores']
            
            for vid_id in video_ids:
                if vid_id in video_map:
                    v = video_map[vid_id]
                    videos_data.append(CollectionVideo(
                        id=v.id,
                        title=v.title,
                        author=v.author,
                        url=v.url,
                        score=scores_map.get(vid_id),
                        snippet=None,  # We don't store snippets in collections
                        description=v.description,
                        clip_count=v.clip_count,
                        hashtags=v.hashtags if hasattr(v, 'hashtags') else None
                    ))
        
        similar_collections.append(SimilarCollectionResult(
            id=collection_id,
            query=query_text,
            similarity=float(similarity),
            ai_answer=ai_answer,
            videos=videos_data,
            created_at=created_at.isoformat() if created_at else "",
            metadata_json=metadata_json or {}
        ))
    
    print(f"[similar-collections] Returning {len(similar_collections)} collections")
    return SimilarCollectionsResponse(
        query=payload.query,
        collections=similar_collections
    )


