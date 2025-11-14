from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes_search import router as search_router
from .db import engine
from sqlalchemy import text
import os

app = FastAPI(title="VidSense Search Service", version="1.0.0")

# Run database migrations on startup
@app.on_event("startup")
def run_migrations():
    print("[startup] Running database migrations...")
    with engine.connect() as conn:
        # Read and execute migration SQL
        sql_file = os.path.join(os.path.dirname(__file__), "sql", "add_retrieval_feedback.sql")
        if os.path.exists(sql_file):
            with open(sql_file, 'r') as f:
                sql_content = f.read()
                # Execute each statement separately
                for statement in sql_content.split(';'):
                    if statement.strip():
                        try:
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            print(f"[startup] Migration statement skipped (may already exist): {e}")
            print("[startup] Database migrations completed")
        else:
            print("[startup] No migration file found")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(search_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "search"}

