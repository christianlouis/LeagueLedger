"""
Router for convenience redirects to simplify common URL patterns.
"""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Convenience"])

@router.get("/scan")
async def scan_redirect():
    """Redirect /scan to /dashboard/scan"""
    return RedirectResponse("/dashboard/scan", status_code=303)

@router.get("/login")
async def login_redirect():
    """Redirect /login to /auth/login"""
    return RedirectResponse("/auth/login", status_code=303)

@router.get("/register")
async def register_redirect():
    """Redirect /register to /auth/register"""
    return RedirectResponse("/auth/register", status_code=303)

@router.get("/profile")
async def profile_redirect():
    """Redirect /profile to /auth/profile"""
    return RedirectResponse("/auth/profile", status_code=303)

@router.get("/logout")
async def logout_redirect():
    """Redirect /logout to /auth/logout"""
    return RedirectResponse("/auth/logout", status_code=303)
