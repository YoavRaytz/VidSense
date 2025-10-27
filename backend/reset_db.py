# backend/app/reset_db.py
from app.db import engine, Base
from app.models import Video, Transcript

if __name__ == "__main__":
    print("⚠️  Dropping tables: videos, transcripts (if exist)…")
    Base.metadata.drop_all(bind=engine, tables=[Transcript.__table__, Video.__table__])

    print("🧱 Creating tables with current models…")
    Base.metadata.create_all(bind=engine, tables=[Video.__table__, Transcript.__table__])

    print("✅ Done. Tables recreated.")
