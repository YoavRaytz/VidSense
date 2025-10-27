from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from sqlalchemy import text

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://tips:tips123@localhost:5432/tipsdb')
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

# Ensure the pgvector extension is available. This runs at import time and is
# safe to call repeatedly because of IF NOT EXISTS. If the DB isn't ready or
# lacks permissions this will fail silently and table creation may error later.
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
except Exception:
    # Defer handling to the part of the app that creates tables; keep import-time
    # errors non-fatal so container can retry if DB becomes ready later.
    pass


def _get_pgvector_version(conn) -> tuple:
    """Return pgvector extension version as a tuple of ints, e.g., (0, 7, 0).
    Returns (0, 0, 0) if not available.
    """
    try:
        res = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        row = res.first()
        if not row or not row[0]:
            return (0, 0, 0)
        parts = str(row[0]).split('.')
        return tuple(int(p) for p in (parts + ['0', '0'])[:3])
    except Exception:
        return (0, 0, 0)


def ensure_vector_indexes():
    """Create ANN index on transcripts.embedding using HNSW when available, else IVFFlat.

    Safe to run multiple times; uses IF NOT EXISTS. Should be called after tables exist.
    """
    try:
        with engine.begin() as conn:
            version = _get_pgvector_version(conn)
            # Prefer HNSW if pgvector >= 0.6.0
            if version >= (0, 6, 0):
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS transcripts_embedding_hnsw
                        ON transcripts
                        USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 200)
                        """
                    )
                )
            else:
                # Fallback to IVFFlat
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS transcripts_embedding_ivfflat
                        ON transcripts
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 1000)
                        """
                    )
                )
    except Exception:
        # Non-fatal; the API can operate without the index albeit slower.
        pass

from typing import Generator

def get_db() -> Generator:
    """FastAPI dependency that yields a Session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
