from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import os, sqlite3, json

app = FastAPI()

UPLOAD_DIR = "uploads"
PASSWORD = "secret123"  # replace with env var in prod
MAX_SIZE = 50 * 1024 * 1024  # 50MB

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

def check_password(pw: str = Form(...)):
    if pw != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/", response_class=HTMLResponse)
def upload_form():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>File Drop Upload</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 flex items-center justify-center min-h-screen">
        <div class="bg-white p-8 rounded shadow-md w-full max-w-md">
            <h1 class="text-2xl font-bold mb-4">File Drop Upload</h1>
            <form action="/" method="post" enctype="multipart/form-data" class="space-y-4">
                <input type="password" name="pw" placeholder="Password" required class="block w-full px-3 py-2 border rounded" />
                <input type="text" name="slug" placeholder="Custom URL slug" required class="block w-full px-3 py-2 border rounded" />
                <input type="number" name="days" min="1" max="7" value="1" required class="block w-full px-3 py-2 border rounded" />
                <input type="file" name="files" multiple required class="block w-full" />
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Upload</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/")
async def upload(
    pw: str = Depends(check_password),
    slug: str = Form(...),
    days: int = Form(...),
    request: Request = None
):
    # Get files from form-data
    form = await request.form()
    files = form.getlist("files")
    if days > 7:
        raise HTTPException(400, "Max expiry is 7 days")
    if not slug.isalnum():
        raise HTTPException(400, "Slug must be alphanumeric")

    # check total size
    total_size = 0
    os.makedirs(f"{UPLOAD_DIR}/{slug}", exist_ok=True)
    paths = []
    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_SIZE:
            raise HTTPException(400, "Upload exceeds 50MB limit")
        path = f"{UPLOAD_DIR}/{slug}/{file.filename}"
        with open(path, "wb") as f:
            f.write(content)
        paths.append(path)

    expiry = datetime.utcnow() + timedelta(days=days)
    cur.execute("INSERT OR REPLACE INTO links (slug, expiry, files) VALUES (?, ?, ?)",
                (slug, expiry.isoformat(), json.dumps(paths)))
    conn.commit()

    return RedirectResponse(f"/{slug}", status_code=303)

@app.get("/{slug}", response_class=HTMLResponse)
def get_files(slug: str):
    cur.execute("SELECT expiry, files FROM links WHERE slug=?", (slug,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Link not found")

    expiry, files_json = row
    if datetime.utcnow() > datetime.fromisoformat(expiry):
        raise HTTPException(410, "Link expired")

    files = json.loads(files_json)
    links = [f'<li><a href="/download/{slug}/{os.path.basename(f)}">{os.path.basename(f)}</a></li>' for f in files]
    return f"""
    <h3 class="text-xl font-bold mb-2">Files for <span class="font-mono">{slug}</span></h3>
    <ul class="list-disc pl-5">{''.join(links)}</ul>
    <p class="mt-4 text-gray-500">Expires: {expiry}</p>
    """

@app.get("/download/{slug}/{filename}")
def download_file(slug: str, filename: str):
    path = f"{UPLOAD_DIR}/{slug}/{filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)
