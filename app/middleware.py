from fastapi import Request, Response

def setup_middleware(app):
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
