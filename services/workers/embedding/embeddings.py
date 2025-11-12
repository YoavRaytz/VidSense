# backend/app/embeddings.py
"""
Embedding service using sentence-transformers for semantic search.
Uses 384-dim model to match the Vector(384) column in the database.
"""
import os
from typing import List, Optional
import numpy as np

# Lazy import to avoid loading model at import time
_model = None
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions


def get_embedding_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"[embeddings] Loading model: {_MODEL_NAME}")
            _model = SentenceTransformer(_MODEL_NAME)
            print(f"[embeddings] Model loaded successfully")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


def embed_text(text: str) -> List[float]:
    """
    Generate a 384-dim embedding for the given text.
    
    Args:
        text: The text to embed (query, transcript, or combined text)
    
    Returns:
        List of 384 floats representing the embedding vector
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * 384
    
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    
    # Convert to list for JSON serialization and database storage
    return embedding.tolist()


def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single batch (more efficient).
    
    Args:
        texts: List of texts to embed
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    
    return [emb.tolist() for emb in embeddings]


def combine_text_for_embedding(transcript: Optional[str], caption: Optional[str]) -> str:
    """
    Combine transcript and caption/description into a single text for embedding.
    
    Strategy: Caption first (usually concise context), then transcript.
    Truncate if too long (model has token limits).
    
    Args:
        transcript: The full transcript text
        caption: The video caption/description
    
    Returns:
        Combined text suitable for embedding
    """
    parts = []
    
    if caption and caption.strip():
        parts.append(f"Caption: {caption.strip()}")
    
    if transcript and transcript.strip():
        parts.append(f"Transcript: {transcript.strip()}")
    
    combined = "\n\n".join(parts)
    
    # Truncate if too long (typical transformers limit ~512 tokens, ~2000 chars safe)
    MAX_CHARS = 5000
    if len(combined) > MAX_CHARS:
        combined = combined[:MAX_CHARS] + "..."
    
    return combined


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Note: If vectors are already normalized, this is just the dot product.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Similarity score between -1 and 1 (higher is more similar)
    """
    # Our embeddings are normalized, so dot product = cosine similarity
    return float(np.dot(vec1, vec2))
