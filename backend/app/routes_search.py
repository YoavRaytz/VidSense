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
from .models import Video, Transcript
from .transcribe.gemini_client import GeminiTranscriber

router = APIRouter(prefix="/search", tags=["search"])


# ========== Schemas ==========

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    k_ann: int | None = Field(default=None, ge=1, description="Number of candidates for ANN search (reranking)")


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
    Semantic search over video transcripts using vector similarity.
    
    Process:
    1. Embed the query
    2. Perform cosine similarity search against transcripts.embedding
    3. Optionally rerank top-k_ann results
    4. Return top-k final results with snippets
    """
    print(f"[search] query='{payload.query}' k={payload.k}")
    
    if not payload.query.strip():
        return SearchResponse(query=payload.query, hits=[], total=0)
    
    # Generate query embedding
    try:
        query_embedding = embed_text(payload.query)
    except Exception as e:
        print(f"[search][ERROR] embedding failed: {e}")
        raise HTTPException(500, f"Failed to generate query embedding: {e}")
    
    # Determine how many candidates to retrieve
    k_retrieve = payload.k_ann or payload.k
    
    # Perform vector similarity search using pgvector
    # Note: <=> is cosine distance operator (lower is better), so we negate for similarity score
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
            1 - (t.embedding <=> :query_vec) AS similarity_score
        FROM transcripts t
        JOIN videos v ON t.video_id = v.id
        WHERE t.embedding IS NOT NULL
        ORDER BY t.embedding <=> :query_vec
        LIMIT :limit
    """)
    
    try:
        result = db.execute(
            sql,
            {"query_vec": json.dumps(query_embedding), "limit": k_retrieve}
        ).fetchall()
    except Exception as e:
        print(f"[search][ERROR] database query failed: {e}")
        raise HTTPException(500, f"Database search failed: {e}")
    
    print(f"[search] found {len(result)} candidates")
    
    # Convert to hits with snippets
    hits = []
    for row in result:
        video_id, title, author, url, source, description, media_path, text, score = row
        
        # Generate snippet (extract relevant portion around query terms)
        snippet = _generate_snippet(text or "", payload.query, max_length=200)
        
        hits.append(SearchHit(
            video_id=video_id,
            title=title,
            author=author,
            url=url,
            source=source,
            description=description,
            media_path=media_path,
            score=float(score),
            snippet=snippet
        ))
    
    # Optional: Rerank if k_ann was specified
    if payload.k_ann and payload.k_ann > payload.k:
        print(f"[search] reranking from {len(hits)} to {payload.k}")
        hits = _rerank_results(payload.query, hits)
    
    # Return top-k
    final_hits = hits[:payload.k]
    
    print(f"[search] returning {len(final_hits)} results")
    return SearchResponse(
        query=payload.query,
        hits=final_hits,
        total=len(result)
    )


# ========== RAG Endpoint ==========

@router.post("/rag", response_model=RAGResponse)
def rag_answer(payload: RAGRequest, db: Session = Depends(get_db)):
    """
    Retrieval-Augmented Generation: Answer questions using video transcripts.
    
    Process:
    1. Search for relevant videos (k_ann candidates)
    2. Rerank and select top k_final sources
    3. Build context with source citations
    4. Generate answer using Gemini with citations [1], [2], etc.
    5. Return answer + sources
    """
    print(f"[rag] query='{payload.query}' k_ann={payload.k_ann} k_final={payload.k_final}")
    
    if not payload.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    
    # Step 1: Retrieve candidates using vector search
    search_req = SearchRequest(query=payload.query, k=payload.k_ann, k_ann=None)
    search_result = search_videos(search_req, db)
    
    if not search_result.hits:
        return RAGResponse(
            query=payload.query,
            answer="I couldn't find any relevant information in the video database to answer your question.",
            sources=[]
        )
    
    # Step 2: Take top k_final for RAG
    top_hits = search_result.hits[:payload.k_final]
    
    # Step 3: Build context with numbered sources
    context_parts = []
    sources = []
    
    for idx, hit in enumerate(top_hits, 1):
        # Get full transcript
        transcript_obj = db.get(Transcript, hit.video_id)
        transcript_text: str = hit.snippet  # default
        if transcript_obj:
            text_val = transcript_obj.text
            if text_val is not None:
                transcript_text = str(text_val)
        
        # Truncate very long transcripts
        if len(transcript_text) > 3000:
            transcript_text = transcript_text[:3000] + "..."
        
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
    
    # Step 4: Generate answer with Gemini
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
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        answer = getattr(response, "text", None) or "Failed to generate answer."
        
    except Exception as e:
        print(f"[rag][ERROR] generation failed: {e}")
        raise HTTPException(500, f"Failed to generate answer: {e}")
    
    print(f"[rag] generated answer with {len(sources)} sources")
    
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
