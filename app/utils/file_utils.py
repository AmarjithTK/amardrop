import os
import json
from fastapi import UploadFile, HTTPException
from app.config import settings

async def process_uploads(files, slug):
    """Process uploaded files and save them to the specified directory."""
    total_size = 0
    saved_files = []
    folder = os.path.join(settings.UPLOAD_DIR, slug)
    os.makedirs(folder, exist_ok=True)
    
    for file in files:
        if isinstance(file, UploadFile) and file.filename:
            safe_filename = os.path.basename(file.filename)
            file_path = os.path.join(folder, safe_filename)
            
            # Read the file content
            content = await file.read()
            total_size += len(content)
            
            # Write the content to disk
            with open(file_path, "wb") as f:
                f.write(content)
            
            saved_files.append(os.path.join(settings.UPLOAD_DIR, slug, safe_filename))
    
    return saved_files, total_size

def cleanup_files(slug, files_json):
    """Delete files associated with a slug."""
    files = json.loads(files_json) if files_json else []
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
            
    # Delete folder if empty
    folder = os.path.join(settings.UPLOAD_DIR, slug)
    if os.path.isdir(folder) and not os.listdir(folder):
        try:
            os.rmdir(folder)
        except Exception:
            pass
