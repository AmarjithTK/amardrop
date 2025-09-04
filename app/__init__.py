# Initialize the app package
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.config import settings
from app.db import init_db
from app.routes import register_routes
from app.middleware import setup_middleware
from app.background import start_background_tasks

def create_app():
    app = FastAPI()
    
    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Configure middleware
    setup_middleware(app)
    
    # Mount static files
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    
    # Register routes
    register_routes(app)
    
    # Start background tasks
    start_background_tasks(app)
    
    return app
