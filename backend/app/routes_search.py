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
from .models import Video, Transcript
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
    
    Process:
    1. Stage 1+2: Retrieve k_ann candidates and rerank with cross-encoder
    2. Select top k_final sources
    3. Build context with source citations
    4. Generate answer using Gemini with citations [1], [2], etc.
    5. Return answer + sources
    """
    print(f"[rag] ========== NEW RAG REQUEST ==========")
    print(f"[rag] Query: '{payload.query}'")
    print(f"[rag] k_ann={payload.k_ann}, k_final={payload.k_final}")
    
    if not payload.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    
    # Step 1+2: Retrieve and rerank using search endpoint
    search_req = SearchRequest(query=payload.query, k=payload.k_final, k_ann=payload.k_ann)
    search_result = search_videos(search_req, db)
    
    if not search_result.hits:
        print(f"[rag] No results found")
        return RAGResponse(
            query=payload.query,
            answer="I couldn't find any relevant information in the video database to answer your question.",
            sources=[]
        )
    
    # Step 2: Use the reranked results (already top k_final)
    top_hits = search_result.hits
    print(f"[rag] Using {len(top_hits)} sources for answer generation")
    
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
