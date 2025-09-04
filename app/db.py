import sqlite3
from contextlib import contextmanager
import json
from datetime import datetime
from app.config import settings

# Global connection
conn = None
cur = None

def init_db():
    global conn, cur
    conn = sqlite3.connect(settings.DATABASE_URL, check_same_thread=False)
    cur = conn.cursor()
    
    # Create tables if they don't exist
    cur.execute("""CREATE TABLE IF NOT EXISTS links (
        slug TEXT PRIMARY KEY,
        expiry TIMESTAMP,
        files TEXT
    )""")
    conn.commit()

@contextmanager
def get_cursor():
    global conn, cur
    if not conn:
        init_db()
    try:
        yield cur
    finally:
        pass  # Connection is managed globally

def save_link(slug, files, days):
    expiry = datetime.utcnow() + datetime.timedelta(days=days)
    with get_cursor() as cursor:
        cursor.execute("INSERT OR REPLACE INTO links (slug, expiry, files) VALUES (?, ?, ?)",
                    (slug, expiry.isoformat(), json.dumps(files)))
        conn.commit()

def get_link(slug):
    with get_cursor() as cursor:
        cursor.execute("SELECT expiry, files FROM links WHERE slug=?", (slug,))
        return cursor.fetchone()

def delete_link(slug):
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM links WHERE slug=?", (slug,))
        conn.commit()

def get_all_links():
    with get_cursor() as cursor:
        cursor.execute("SELECT slug, expiry, files FROM links")
        return cursor.fetchall()
