from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from datetime import datetime, timedelta
import os, sqlite3, json, threading, time, re
import bcrypt

app = FastAPI()

UPLOAD_DIR = "uploads"
TEMPLATES_DIR = "templates"
MAX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES = 10  # Max files per upload
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}

# Secure password from env and hash
RAW_PASSWORD = os.environ.get("AMARDROP_PASSWORD", "changeMe123")
PASSWORD_HASH = bcrypt.hashpw(RAW_PASSWORD.encode(), bcrypt.gensalt())

# Ensure uploads directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- DB setup ---
conn = sqlite3.connect("files.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS links (
    slug TEXT PRIMARY KEY,
    expiry TIMESTAMP,
    files TEXT
)""")
conn.commit()

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Secure headers middleware
@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "font-src 'self' https://cdn.tailwindcss.com https://unpkg.com; "
        "img-src 'self' data: blob:;"
    )
    return response

def check_password(pw: str = Form(...)):
    if not bcrypt.checkpw(pw.encode(), PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid password")

def is_safe_filename(filename):
    # Prevent directory traversal and enforce allowed extensions
    if "/" in filename or "\\" in filename or ".." in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def is_safe_slug(slug):
    return re.match(r'^[a-zA-Z0-9]+$', slug) is not None

@app.get("/", response_class=None)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/")
async def upload(
    request: Request,
    pw: str = Depends(check_password),
    slug: str = Form(...),
    days: int = Form(...),
):
    form = await request.form()
    files = form.getlist("files")
    if days > 7:
        raise HTTPException(400, "Max expiry is 7 days")
    if not is_safe_slug(slug):
        raise HTTPException(400, "Slug must be alphanumeric")
    if len(files) == 0:
        raise HTTPException(400, "At least one file required")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Max {MAX_FILES} files per upload")

    total_size = 0
    os.makedirs(f"{UPLOAD_DIR}/{slug}", exist_ok=True)
    # Retrieve existing files and expiry for this slug if any
    cur.execute("SELECT expiry, files FROM links WHERE slug=?", (slug,))
    row = cur.fetchone()
    existing_files = []
    existing_expiry = None
    if row:
        existing_expiry, files_json = row
        # If not expired, do not allow upload to this slug
        if datetime.utcnow() <= datetime.fromisoformat(existing_expiry):
            raise HTTPException(409, "Slug is already in use and not expired")
        # If expired, allow reuse and cleanup old files
        existing_files = []
        folder = os.path.join(UPLOAD_DIR, slug)
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                try:
                    os.remove(os.path.join(folder, f))
                except Exception:
                    pass

    paths = []
    for file in files:
        filename = os.path.basename(file.filename)
        if not is_safe_filename(filename):
            raise HTTPException(400, f"Unsafe or disallowed file type: {filename}")
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_SIZE:
            raise HTTPException(400, "Upload exceeds 50MB limit")
        path = f"{UPLOAD_DIR}/{slug}/{filename}"
        with open(path, "wb") as f:
            f.write(content)
        if path not in paths:
            paths.append(path)

    # Set expiry to new value
    expiry = datetime.utcnow() + timedelta(days=days)

    cur.execute("INSERT OR REPLACE INTO links (slug, expiry, files) VALUES (?, ?, ?)",
                (slug, expiry.isoformat(), json.dumps(paths)))
    conn.commit()

    return RedirectResponse(f"/{slug}", status_code=303)

@app.get("/{slug}", response_class=None)
def get_files(request: Request, slug: str):
    cur.execute("SELECT expiry, files FROM links WHERE slug=?", (slug,))
    row = cur.fetchone()
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

@app.get("/download/{slug}/{filename}")
def download_file(slug: str, filename: str):
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    path = f"{UPLOAD_DIR}/{slug}/{safe_filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=safe_filename)

def cleanup_expired():
    while True:
        now = datetime.utcnow()
        cur.execute("SELECT slug, expiry, files FROM links")
        rows = cur.fetchall()
        for slug, expiry, files_json in rows:
            if expiry and now > datetime.fromisoformat(expiry):
                # Delete files
                files = json.loads(files_json) if files_json else []
                for f in files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                # Delete folder if empty
                folder = os.path.join(UPLOAD_DIR, slug)
                if os.path.isdir(folder) and not os.listdir(folder):
                    try:
                        os.rmdir(folder)
                    except Exception:
                        pass
                # Remove DB entry
                cur.execute("DELETE FROM links WHERE slug=?", (slug,))
                conn.commit()
        time.sleep(24 * 60 * 60)  # Run once a day

@app.on_event("startup")
def start_cleanup_thread():
    t = threading.Thread(target=cleanup_expired, daemon=True)
    t.start()

# Possible anomalies users could experience:
# 1. Upload fails if slug is already in use and not expired (409 error).
# 2. Upload fails if total file size exceeds 50MB (400 error).
# 3. Upload fails if password is incorrect (401 error).
# 4. Upload fails if expiry days > 7 (400 error).
# 5. Upload fails if slug contains non-alphanumeric characters (400 error).
# 6. Download fails if file does not exist (404 error).
# 7. Download page fails if slug does not exist (404 error).
# 8. Download page fails if slug is expired (410 error).
# 9. If two users try to upload to the same slug at the same time, one will get a 409 error.
# 10. If files are deleted manually from disk, download links will break (404 error).
# 11. If database or disk is full, uploads may silently fail or cause server errors.
# 12. If server restarts, background cleanup thread may not run immediately.
# 13. If template files are missing or corrupted, pages will not render.
# 14. If user uploads files with the same name as existing files in the slug, old files are overwritten.
# 15. If browser or network disconnects during upload, files may be partially saved.
# 16. If SQLite database gets locked or corrupted, all operations may fail.
# 17. If user tries to upload zero files, the slug will be created with no files.
# 18. If system time changes (e.g., daylight saving), expiry calculations may be affected.
# 19. If a slug is reused immediately after expiry, old files may not be fully cleaned up before new upload.
# 20. If multiple users upload large files simultaneously, server performance may degrade.



