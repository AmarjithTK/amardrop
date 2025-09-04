import re
from fastapi import HTTPException, Request
from app.config import settings

def is_safe_slug(slug):
    """Validate that slug is safe to use as a folder name."""
    return bool(re.match(r'^[a-zA-Z0-9-_]+$', slug))

async def check_password(request: Request):
    """Extract and validate password from request form."""
    form = await request.form()
    if "pw" not in form:
        raise HTTPException(401, "Password required")
    pw = form["pw"]
    
    if pw != settings.UPLOAD_PASSWORD:
        raise HTTPException(401, "Invalid password")
    
    return pw
