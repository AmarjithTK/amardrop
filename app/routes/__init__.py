from fastapi import FastAPI
from app.routes.upload import router as upload_router
from app.routes.download import router as download_router

def register_routes(app: FastAPI):
    app.include_router(upload_router)
    app.include_router(download_router)
