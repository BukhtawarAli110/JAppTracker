"""WSGI entry point for production servers like gunicorn on Render."""
from app import app
from reminders import start_scheduler

# Start the background scheduler once, inside the gunicorn worker
start_scheduler()
