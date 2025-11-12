# services/ingestion/app/celery_client.py
import os
from celery import Celery

# Celery client for sending tasks to workers
celery_app = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

# Configure to not require results for fire-and-forget tasks
celery_app.conf.update(
    task_ignore_result=True,
    task_track_started=False,
)
