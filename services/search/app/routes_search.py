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


class RAGSource(BaseModel):
    video_id: str
    title: str | None
    author: str | None
    url: str
    snippet: str
    score: float


class RAGResponse(BaseModel):
    query: str
    answer: str = Field(description="AI-generated answer with inline citations")
    sources: List[RAGSource] = Field(description="Source videos used to generate the answer")


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
    
    Enhanced with retrieval feedback:
    1. Find similar past queries
    2. Include 'good' sources from similar queries in context
    3. Exclude 'bad' sources and already-retrieved sources from search
    4. Generate answer with Gemini using combined sources
    """
    print(f"[rag] ========== NEW RAG REQUEST ==========")
    print(f"[rag] Query: '{payload.query}'")
    print(f"[rag] k_ann={payload.k_ann}, k_final={payload.k_final}")
    
    if not payload.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    
    # Step 0: Find similar past queries and get their feedback
    print(f"[rag] Step 0: Finding similar past queries...")
    similar_queries_result = find_similar_queries(
        SearchRequest(query=payload.query, k=payload.k_final, k_ann=payload.k_ann),
        db
    )
    
    # Collect good and bad video IDs from similar queries
    good_video_ids_from_past = set()
    bad_video_ids_from_past = set()
    
    for sim_query in similar_queries_result.similar_queries:
        print(f"[rag] Similar query found: '{sim_query.query}' (similarity={sim_query.similarity:.4f})")
        print(f"[rag]   Good sources: {len(sim_query.good_video_ids)}, Bad sources: {len(sim_query.bad_video_ids)}")
        good_video_ids_from_past.update(sim_query.good_video_ids)
        bad_video_ids_from_past.update(sim_query.bad_video_ids)
    
    exclude_video_ids = good_video_ids_from_past | bad_video_ids_from_past
    print(f"[rag] Excluding {len(exclude_video_ids)} already-retrieved videos from search")
    print(f"[rag]   {len(good_video_ids_from_past)} good sources to include in context")
    print(f"[rag]   {len(bad_video_ids_from_past)} bad sources to exclude")
    
    # Step 1+2: Retrieve and rerank using search endpoint (with exclusions)
    search_req = SearchRequest(query=payload.query, k=payload.k_final * 2, k_ann=payload.k_ann)
    search_result = search_videos(search_req, db)
    
    # Filter out excluded videos from new search results
    filtered_hits = [hit for hit in search_result.hits if hit.video_id not in exclude_video_ids]
    print(f"[rag] Filtered search results: {len(filtered_hits)} results (from {len(search_result.hits)} original)")
    
    # Step 2: Fetch good sources from similar queries
    good_sources_from_past = []
    if good_video_ids_from_past:
        print(f"[rag] Fetching {len(good_video_ids_from_past)} good sources from past queries...")
        for video_id in good_video_ids_from_past:
            video = db.get(Video, video_id)
            transcript = db.get(Transcript, video_id)
            if video is not None and transcript is not None:
                transcript_text = getattr(transcript, 'text', '') or ''
                snippet = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
                good_sources_from_past.append(SearchHit(
                    video_id=getattr(video, 'id'),
                    title=getattr(video, 'title', None),
                    author=getattr(video, 'author', None),
                    url=getattr(video, 'url'),
                    score=1.0,  # High confidence from past feedback
                    snippet=snippet,
                    media_path=getattr(video, 'media_path', None),
                    source=getattr(video, 'source', None),
                    description=getattr(video, 'description', None)
                ))
    
    # Combine: good sources from past + new filtered search results
    all_hits = good_sources_from_past + filtered_hits
    top_hits = all_hits[:payload.k_final]
    
    if not top_hits:
        print(f"[rag] No results found after filtering")
        return RAGResponse(
            query=payload.query,
            answer="I couldn't find any relevant information in the video database to answer your question.",
            sources=[]
        )
    
    print(f"[rag] Using {len(top_hits)} sources for answer generation ({len(good_sources_from_past)} from past, {len(filtered_hits[:payload.k_final-len(good_sources_from_past)])} new)")
    
    # Step 3: Build context with numbered sources
    context_parts = []
    sources = []
    
    for idx, hit in enumerate(top_hits, 1):
        title = hit.title or 'Untitled'
        title_display = title[:40] if len(title) > 40 else title
        print(f"[rag] Source [{idx}]: video_id={hit.video_id[:16]}..., score={hit.score:.4f}, title={title_display}")
        
        # Get full transcript
        transcript_obj = db.get(Transcript, hit.video_id)
        transcript_text: str = hit.snippet  # default
        if transcript_obj:
            text_val = transcript_obj.text
            if text_val is not None:
                transcript_text = str(text_val)
        
        # Truncate very long transcripts
        original_len = len(transcript_text)
        if len(transcript_text) > 3000:
            transcript_text = transcript_text[:3000] + "..."
            print(f"[rag]   Truncated transcript from {original_len} to 3000 chars")
        
        context_parts.append(f"[Source {idx}] {hit.title or 'Untitled'}\n{transcript_text}\n")
        
        sources.append(RAGSource(
            video_id=hit.video_id,
            title=hit.title,
            author=hit.author,
            url=hit.url,
            snippet=hit.snippet,
            score=hit.score
        ))
    
    context = "\n\n".join(context_parts)
    print(f"[rag] Built context with {len(context)} characters from {len(sources)} sources")
    
    # Step 4: Generate answer with Gemini
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
    
    print(f"[rag] Returning answer with {len(sources)} sources")
    print(f"[rag] ========== RAG COMPLETE ==========\n")
    
    return RAGResponse(
        query=payload.query,
        answer=answer,
        sources=sources
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
    
    # Save feedback
    try:
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
        raise HTTPException(500, f"Failed to save feedback: {e}")


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


