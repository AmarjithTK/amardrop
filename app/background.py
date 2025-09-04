import threading
import time
from datetime import datetime
from app.db import get_all_links, delete_link
from app.utils.file_utils import cleanup_files

def cleanup_expired():
    """Background task to clean up expired links and files."""
    while True:
        now = datetime.utcnow()
        rows = get_all_links()
        for slug, expiry, files_json in rows:
            if expiry and now > datetime.fromisoformat(expiry):
                # Delete files
                cleanup_files(slug, files_json)
                # Remove DB entry
                delete_link(slug)
        time.sleep(24 * 60 * 60)  # Run once a day

def start_background_tasks(app):
    @app.on_event("startup")
    def start_cleanup_thread():
        t = threading.Thread(target=cleanup_expired, daemon=True)
        t.start()
