"""
Cross-Encoder Reranker for RAG systems
Uses ms-marco-MiniLM-L-6-v2 to re-rank documents by relevance to query
"""
from __future__ import annotations

from typing import List, Dict
import threading
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _get_tokenizer():
    """Lazy-load tokenizer (cached)"""
    print(f"[reranker] Loading tokenizer: {_model_name}")
    return AutoTokenizer.from_pretrained(_model_name)


@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load model (cached)"""
    print(f"[reranker] Loading model: {_model_name}")
    model = AutoModelForSequenceClassification.from_pretrained(_model_name)
    model.eval()
    print(f"[reranker] Model loaded successfully")
    return model


def rerank(query: str, docs: List[Dict], text_key: str = "text") -> List[Dict]:
    """
    Re-rank documents using Cross-Encoder.
    
    Args:
        query: User query string
        docs: List of dicts with at least {text_key: str}
        text_key: Key name for document text (default: "text")
    
    Returns:
        List of docs sorted by rerank_score (highest first)
        Adds "rerank_score" field to each doc
    
    Fallback:
        If model fails to load/run, returns docs in original order with score=0.0
    """
    if not docs:
        print(f"[reranker] No documents to rerank")
        return []
    
    print(f"[reranker] Reranking {len(docs)} documents for query: '{query[:50]}...'")
    
    # Smart text extraction: find query terms and send relevant section
    pairs = []
    for i, doc in enumerate(docs):
        full_text = doc.get(text_key, "")
        video_id = doc.get("video_id", "unknown")[:16]
        
        print(f"[reranker] Doc {i+1}/{len(docs)}: video_id={video_id}, text_length={len(full_text)}")
        
        # Try to find query terms in the text
        query_lower = query.lower()
        text_lower = full_text.lower()
        
        # Find best matching section
        best_section = full_text
        found_match = False
        
        # Try each word in the query
        for word in query_lower.split():
            if len(word) > 2:  # Skip very short words like "a"
                pos = text_lower.find(word)
                if pos >= 0:
                    # Extract window around the match (2000 chars before, 2000 after)
                    start = max(0, pos - 2000)
                    end = min(len(full_text), pos + 2000)
                    best_section = full_text#[start:end]
                    print(f"[reranker]   Found '{word}' at position {pos}, using section [{start}:{end}] ({len(best_section)} chars)")
                    found_match = True
                    break
        
        if not found_match:
            print(f"[reranker]   No query terms found, using first {min(len(full_text), 4000)} chars")
            best_section = full_text[:4000]
        
        pairs.append((query, best_section))
    
    try:
        # Thread-safe model loading
        with _lock:
            tok = _get_tokenizer()
            model = _get_model()
        
        print(f"[reranker] Tokenizing {len(pairs)} query-document pairs...")
        
        # Tokenize query-doc pairs (max_length=512 for better context)
        inputs = tok.batch_encode_plus(
            pairs, 
            padding=True, 
            truncation=True, 
            return_tensors="pt", 
            max_length=512
        )
        
        print(f"[reranker] Computing relevance scores...")
        
        # Compute relevance scores
        with torch.no_grad():
            logits = model(**inputs).logits
            # Handle models that return shape (batch, 1)
            scores = logits.squeeze(-1).detach().cpu().tolist()
            if isinstance(scores, float):
                scores = [scores]
        
        print(f"[reranker] Raw logit range: [{min(scores):.4f}, {max(scores):.4f}]")
        
        # Attach scores and sort
        for d, s in zip(docs, scores):
            d["rerank_score"] = float(s)
        
        ranked = sorted(docs, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        
        # Debug: print score distribution
        if ranked:
            top_score = ranked[0].get("rerank_score", 0.0)
            bottom_score = ranked[-1].get("rerank_score", 0.0)
            print(f"[reranker] After sorting - Top score: {top_score:.4f}, Bottom: {bottom_score:.4f}]")
            print(f"[reranker] Top 3 results:")
            for i, doc in enumerate(ranked[:3], 1):
                title = doc.get("title") or "Untitled"
                title = title[:40] if len(title) > 40 else title
                score = doc.get("rerank_score", 0.0)
                video_id = doc.get("video_id", "unknown")[:16]
                print(f"[reranker]   #{i}: score={score:.4f}, video_id={video_id}, title={title}")
        
        return ranked
    
    except Exception as e:
        # Fallback: return original ANN order if reranking fails
        print(f"[reranker][WARNING] Reranker failed: {e}. Using ANN order.")
        import traceback
        traceback.print_exc()
        for d in docs:
            d.setdefault("rerank_score", 0.0)
        return docs
