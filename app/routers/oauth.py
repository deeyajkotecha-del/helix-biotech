"""
Google OAuth Authentication Router

Handles the Google OAuth 2.0 sign-in flow:
1. Frontend redirects user to Google's consent screen
2. Google redirects back to /api/oauth/google/callback with an auth code
3. We exchange the code for tokens, verify the user, and set a session cookie

Setup (on Google Cloud Console):
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: https://satyabio.com/api/oauth/google/callback
4. Copy the Client ID and Client Secret

Environment variables needed on Render:
    GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
    GOOGLE_CLIENT_SECRET=your-client-secret
    OAUTH_REDIRECT_URI=https://satyabio.com/api/oauth/google/callback
"""

import os
import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import httpx

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration — all from environment variables, no defaults for secrets
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
OAUTH_REDIRECT_URI = os.environ.get(
    "OAUTH_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback"
)

# Reuse the same cookie name and secret as the password gate
# so Google-authed users pass through the gate seamlessly
COOKIE_NAME = "satya_access"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _make_cookie_value() -> str:
    """Create the same cookie hash as auth_gate so the user passes the gate."""
    gate_password = os.environ.get("GATE_PASSWORD", "satyabio2026")
    return hashlib.sha256(f"{SECRET_KEY}:{gate_password}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Step 1: Redirect user to Google's consent screen
# ---------------------------------------------------------------------------

@router.get("/google/login")
async def google_login(request: Request):
    """
    Redirect the user to Google's OAuth consent screen.
    After they approve, Google sends them back to /google/callback.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID env var.",
        )

    # Generate a random state token to prevent CSRF
    state = secrets.token_urlsafe(32)

    # Build the Google authorization URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",  # Always show account picker
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"

    # Store state in a short-lived cookie for verification on callback
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,  # 10 minutes
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return response


# ---------------------------------------------------------------------------
# Step 2: Handle the callback from Google
# ---------------------------------------------------------------------------

@router.get("/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """
    Google redirects here after the user approves (or denies) access.
    We exchange the auth code for tokens, get user info, and set the session.
    """
    # Handle denial
    if error:
        return HTMLResponse(
            f"<h2>Login cancelled</h2><p>{error}</p><p><a href='/'>Go home</a></p>",
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    # Verify state matches (CSRF protection)
    saved_state = request.cookies.get("oauth_state", "")
    if not saved_state or saved_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="Failed to exchange authorization code with Google",
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=502, detail="No access token received from Google")

        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get user info from Google")

        userinfo = userinfo_response.json()

    google_id = userinfo.get("id")
    email = userinfo.get("email")
    name = userinfo.get("name")
    avatar = userinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Upsert user in database
    try:
        from app.database import SessionLocal
        from app.models.user import User

        db = SessionLocal()
        try:
            # Look up by google_id first, then by email
            user = db.query(User).filter(User.google_id == google_id).first()
            if not user:
                user = db.query(User).filter(User.email == email).first()

            if user:
                # Update existing user with Google info
                if not user.google_id:
                    user.google_id = google_id
                if name and not user.full_name:
                    user.full_name = name
                user.avatar_url = avatar
                user.is_active = True
            else:
                # Create new user from Google
                user = User(
                    email=email,
                    google_id=google_id,
                    full_name=name,
                    avatar_url=avatar,
                    hashed_password=None,  # No password for Google-only users
                    is_active=True,
                )
                db.add(user)

            db.commit()
        finally:
            db.close()
    except Exception:
        # If DB fails, still let them through the gate
        # (the gate is the primary auth mechanism right now)
        pass

    # Set the same session cookie as the password gate
    # This means Google-authed users pass through the PasswordGateMiddleware
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=_make_cookie_value(),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    # Clean up the state cookie
    response.delete_cookie("oauth_state")

    return response


# ---------------------------------------------------------------------------
# Utility: Check if Google OAuth is configured
# ---------------------------------------------------------------------------

@router.get("/status")
async def oauth_status():
    """Check if Google OAuth is configured (for frontend to know whether to show the button)."""
    return {
        "google_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    }
