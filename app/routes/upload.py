from fastapi import APIRouter, Form, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
import json

from app.config import settings
from app.utils.security import is_safe_slug, check_password
from app.utils.file_utils import process_uploads
from app.db import get_link, save_link

router = APIRouter()
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

@router.get("/", response_class=None)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/")
async def upload(
    request: Request,
    slug: str = Form(...),
    days: int = Form(...),
):
    try:
        # Check password first
        pw = await check_password(request)
        
        form = await request.form()
        files = form.getlist("files")
        
        if days > settings.MAX_EXPIRY_DAYS:
            raise HTTPException(400, f"Max expiry is {settings.MAX_EXPIRY_DAYS} days")
        if not is_safe_slug(slug):
            raise HTTPException(400, "Slug must be alphanumeric")
        if len(files) == 0:
            raise HTTPException(400, "At least one file required")
        if len(files) > settings.MAX_FILES:
            raise HTTPException(400, f"Max {settings.MAX_FILES} files per upload")

        # Retrieve existing files and expiry for this slug if any
        row = get_link(slug)
        if row:
            expiry, _ = row
            if datetime.utcnow() <= datetime.fromisoformat(expiry):
                raise HTTPException(409, "Slug is already in use and not expired")
            # Cleanup old files is handled by file_utils

        # Modular upload handling
        saved_files, total_size = await process_uploads(files, slug)
        if total_size > settings.MAX_SIZE:
            raise HTTPException(400, f"Upload exceeds {settings.MAX_SIZE // (1024 * 1024)}MB limit")

        save_link(slug, saved_files, days)
        return RedirectResponse(f"/{slug}", status_code=303)
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Log the exception and return a user-friendly error
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
