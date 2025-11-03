from fastapi import FastAPI
from .db import Base, engine, ensure_vector_indexes
# ... your other imports

from . import models  # <-- important

from .routes_ingest import router as ingest_router
from .routes_search import router as search_router
from .routes_collections import router as collections_router


app = FastAPI()

# Wire routers
app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(collections_router)

# Create tables & indexes on startup
@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)
    ensure_vector_indexes()
