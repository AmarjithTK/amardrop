import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    UPLOAD_DIR: str = "uploads"
    TEMPLATES_DIR: str = "templates"
    MAX_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_FILES: int = 50
    DATABASE_URL: str = "files.db"
    UPLOAD_PASSWORD: str = "123"  # Change this to a secure password in production
    MAX_EXPIRY_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        
settings = Settings()
