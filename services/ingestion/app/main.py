from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes_ingest import router as ingest_router

app = FastAPI(title="VidSense Ingestion Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ingest_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ingestion"}
