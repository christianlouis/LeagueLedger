from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

router = APIRouter()

# Function to setup static files that will be called from main.py
def configure_static_files(app):
    """Configure static files mounting for the application."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve favicon.ico
@router.get("/favicon.ico")
async def serve_favicon():
    """Serve favicon.ico."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "favicon.ico")
    return FileResponse(file_path)

# Serve android-chrome-192x192.png
@router.get("/android-chrome-192x192.png")
async def serve_android_chrome_192():
    """Serve android-chrome-192x192.png."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "android-chrome-192x192.png")
    return FileResponse(file_path)

# Serve android-chrome-512x512.png
@router.get("/android-chrome-512x512.png")
async def serve_android_chrome_512():
    """Serve android-chrome-512x512.png."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "android-chrome-512x512.png")
    return FileResponse(file_path)

# Serve apple-touch-icon.png
@router.get("/apple-touch-icon.png")
async def serve_apple_touch_icon():
    """Serve apple-touch-icon.png."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "apple-touch-icon.png")
    return FileResponse(file_path)

# Serve favicon-16x16.png
@router.get("/favicon-16x16.png")
async def serve_favicon_16():
    """Serve favicon-16x16.png."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "favicon-16x16.png")
    return FileResponse(file_path)

# Serve favicon-32x32.png
@router.get("/favicon-32x32.png")
async def serve_favicon_32():
    """Serve favicon-32x32.png."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "favicon-32x32.png")
    return FileResponse(file_path)

# Serve site.webmanifest
@router.get("/images/favicon/site.webmanifest")
async def serve_site_webmanifest():
    """Serve site.webmanifest."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "images", "favicon", "site.webmanifest")
    return FileResponse(file_path)