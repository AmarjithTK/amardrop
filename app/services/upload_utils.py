import os
import zipfile
import io
import re
from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.md'}

def is_safe_slug(slug):
    """Validate that slug is safe to use as a folder name."""
    return bool(re.match(r'^[a-zA-Z0-9-_]+$', slug))

def is_safe_filename(filename):
    if "/" in filename or "\\" in filename or ".." in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

async def process_uploads(files, upload_dir, slug):
    """Process uploaded files and save them to the specified directory."""
    folder_files = []
    regular_files = []
    total_size = 0

    for file in files:
        filename = os.path.basename(file.filename)
        if not is_safe_filename(filename):
            raise HTTPException(400, f"Unsafe or disallowed file type: {filename}")
        # Detect folder upload by presence of "/" in filename (webkitdirectory)
        if "/" in file.filename or "\\" in file.filename:
            folder_files.append(file)
        else:
            regular_files.append(file)

    saved_files = []
    # Save regular files
    for file in regular_files:
        filename = os.path.basename(file.filename)
        content = await file.read()
        total_size += len(content)
        path = os.path.join(upload_dir, slug, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        saved_files.append(path)

    # If folder files exist, zip them together
    if folder_files:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in folder_files:
                arcname = file.filename
                content = await file.read()
                total_size += len(content)
                zipf.writestr(arcname, content)
        zip_name = f"{slug}_folders_{len(folder_files)}.zip"
        zip_path = os.path.join(upload_dir, slug, zip_name)
        with open(zip_path, "wb") as f:
            f.write(zip_buffer.getvalue())
        saved_files.append(zip_path)

    return saved_files, total_size

async def check_password(request):
    """Extract and validate password from request form."""
    form = await request.form()
    if "pw" not in form:
        raise HTTPException(401, "Password required")
    pw = form["pw"]
    
    # Replace this with your actual password check
    expected_password = "123"  # Change this to your secure password
    if pw != expected_password:
        raise HTTPException(401, "Invalid password")
    
    return pw
