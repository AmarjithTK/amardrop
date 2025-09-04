from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import shutil, os, time, sqlite3

app = FastAPI()
UPLOAD_DIR = "uploads"
DB_FILE = "files.db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- DB setup ---
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS files
             (slug TEXT PRIMARY KEY, filename TEXT, expires_at INTEGER)""")
conn.commit()

@app.post("/upload/")
async def upload_file(file: UploadFile, slug: str = Form(...), expiry_minutes: int = Form(60)):
    # Check slug availability
    c.execute("SELECT slug FROM files WHERE slug=?", (slug,))
    if c.fetchone():
        raise HTTPException(status_code=400, detail="Slug already taken")

    # Save file
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save to DB
    expires_at = int(time.time()) + expiry_minutes * 60
    c.execute("INSERT INTO files VALUES (?, ?, ?)", (slug, filepath, expires_at))
    conn.commit()

    return {"url": f"/d/{slug}", "expires_at": expires_at}

@app.get("/d/{slug}")
def download_file(slug: str):
    c.execute("SELECT filename, expires_at FROM files WHERE slug=?", (slug,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    filename, expires_at = row
    if time.time() > expires_at:
        os.remove(filename)
        c.execute("DELETE FROM files WHERE slug=?", (slug,))
        conn.commit()
        raise HTTPException(status_code=410, detail="File expired")

    return FileResponse(filename, filename=os.path.basename(filename))
