from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from datetime import datetime, timedelta
import os, sqlite3, json, threading, time, re, zipfile, io
import bcrypt
from app.services.upload_utils import process_uploads, is_safe_slug, check_password

def create_app():
    app = FastAPI()

    UPLOAD_DIR = "uploads"
    TEMPLATES_DIR = "templates"
    MAX_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_FILES = 50  # Increased for folder support

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

    @app.get("/", response_class=None)
    def upload_form(request: Request):
        return templates.TemplateResponse("upload.html", {"request": request})

    @app.post("/")
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
            
            if days > 7:
                raise HTTPException(400, "Max expiry is 7 days")
            if not is_safe_slug(slug):
                raise HTTPException(400, "Slug must be alphanumeric")
            if len(files) == 0:
                raise HTTPException(400, "At least one file required")
            if len(files) > MAX_FILES:
                raise HTTPException(400, f"Max {MAX_FILES} files per upload")

            # Retrieve existing files and expiry for this slug if any
            cur.execute("SELECT expiry, files FROM links WHERE slug=?", (slug,))
            row = cur.fetchone()
            existing_expiry = None
            if row:
                existing_expiry, existing_files_json = row
                if datetime.utcnow() <= datetime.fromisoformat(existing_expiry):
                    # Slug is in use and not expired, merge new files with existing
                    existing_files = json.loads(existing_files_json)
                else:
                    # Expired, cleanup old files
                    folder = os.path.join(UPLOAD_DIR, slug)
                    if os.path.isdir(folder):
                        for f in os.listdir(folder):
                            try:
                                os.remove(os.path.join(folder, f))
                            except Exception:
                                pass
                    existing_files = []
            else:
                existing_files = []

            # Modular upload handling
            saved_files, total_size = await process_uploads(files, UPLOAD_DIR, slug)
            all_files = existing_files + saved_files
            if total_size > MAX_SIZE:
                raise HTTPException(400, "Upload exceeds 50MB limit")

            expiry = datetime.utcnow() + timedelta(days=days)
            cur.execute("INSERT OR REPLACE INTO links (slug, expiry, files) VALUES (?, ?, ?)",
                        (slug, expiry.isoformat(), json.dumps(all_files)))
            conn.commit()

            return RedirectResponse(f"/{slug}", status_code=303)
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            # Log the exception and return a user-friendly error
            print(f"Upload error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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

    # Update check_password function to handle request directly
    async def check_password(request: Request):
        form = await request.form()
        if "pw" not in form:
            raise HTTPException(401, "Password required")
        pw = form["pw"]
        # Implement your password checking logic here
        # For example:
        if pw != "123":  # Replace with your actual password check
            raise HTTPException(401, "Invalid password")
        return pw

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

