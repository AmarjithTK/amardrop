from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
import json

from app.config import settings
from app.db import get_link

router = APIRouter()
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

@router.get("/{slug}", response_class=None)
def get_files(request: Request, slug: str):
    row = get_link(slug)
    if not row:
        raise HTTPException(404, "Link not found")

    expiry, files_json = row
    if datetime.utcnow() > datetime.fromisoformat(expiry):
        raise HTTPException(410, "Link expired")

    files = json.loads(files_json)
    file_links = [
        {"name": os.path.basename(f), "url": f"/download/{slug}/{os.path.basename(f)}"}
        for f in files
    ]
    return templates.TemplateResponse(
        "download.html",
        {
            "request": request,
            "slug": slug,
            "expiry": expiry,
            "files": file_links,
        },
    )

@router.get("/download/{slug}/{filename}")
def download_file(slug: str, filename: str):
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    path = f"{settings.UPLOAD_DIR}/{slug}/{safe_filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=safe_filename)
