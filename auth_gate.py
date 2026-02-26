"""
Satya Bio — Simple Password Gate Middleware
============================================
Drop this into your FastAPI app to gate your entire site behind a password.

HOW IT WORKS:
1. Every incoming request is intercepted by this middleware.
2. If the user has a valid session cookie ("satya_access"), they pass through.
3. If not, they see a login page where they enter the shared password.
4. On correct password, a cookie is set and they're redirected to the homepage.

HOW TO USE:
1. Copy this file into your project root (next to main.py)
2. In main.py, add these two lines near the top:

    from auth_gate import add_password_gate
    add_password_gate(app)

3. Set your password via environment variable on Render:
   - Go to your Render dashboard → your service → Environment
   - Add: GATE_PASSWORD = "your-secret-password"

4. Push to GitHub → Render auto-deploys → your site is now gated!

TO REMOVE THE GATE LATER:
Just remove the two lines from main.py and redeploy.
"""

import os
import hashlib
import secrets
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The password users must enter. Set via environment variable on Render.
# Falls back to "satyabio2026" if not set (change this!)
GATE_PASSWORD = os.environ.get("GATE_PASSWORD", "satyabio2026")

# Cookie name and settings
COOKIE_NAME = "satya_access"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# A secret key used to sign the cookie so users can't fake it
# Generates a random one on each deploy — meaning users re-auth on redeploy.
# For persistent sessions across deploys, set SECRET_KEY env var on Render.
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))


# ---------------------------------------------------------------------------
# Helper: create a signed cookie value so it can't be faked
# ---------------------------------------------------------------------------
def make_cookie_value() -> str:
    """Create a hash that proves the user entered the correct password."""
    return hashlib.sha256(f"{SECRET_KEY}:{GATE_PASSWORD}".encode()).hexdigest()


def is_valid_cookie(value: str) -> bool:
    """Check if a cookie value matches our expected hash."""
    return value == make_cookie_value()


# ---------------------------------------------------------------------------
# The login page HTML (inline — no extra files needed)
# ---------------------------------------------------------------------------
def get_login_page(error: bool = False) -> str:
    """Return the HTML for the password gate page, styled to match Satya Bio."""
    error_html = ""
    if error:
        error_html = '<p class="error">Incorrect password. Please try again.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satya Bio — Access Required</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Serif+Display&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg: #fafaf8;
            --text: #1a1a2e;
            --text-muted: #6b7280;
            --coral: #e07a5f;
            --coral-hover: #c9694f;
            --coral-light: rgba(224, 122, 95, 0.08);
            --border: #e5e5e0;
            --white: #ffffff;
            --error: #dc2626;
        }}

        body {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }}

        /* Subtle animated background circles — matches your homepage */
        .bg-circle {{
            position: fixed;
            border-radius: 50%;
            opacity: 0.04;
            pointer-events: none;
        }}
        .bg-circle-1 {{
            width: 600px;
            height: 600px;
            background: var(--coral);
            top: -200px;
            right: -100px;
            animation: float1 20s ease-in-out infinite;
        }}
        .bg-circle-2 {{
            width: 400px;
            height: 400px;
            background: var(--coral);
            bottom: -150px;
            left: -100px;
            animation: float2 25s ease-in-out infinite;
        }}

        @keyframes float1 {{
            0%, 100% {{ transform: translate(0, 0); }}
            50% {{ transform: translate(-40px, 30px); }}
        }}
        @keyframes float2 {{
            0%, 100% {{ transform: translate(0, 0); }}
            50% {{ transform: translate(30px, -20px); }}
        }}

        .gate-container {{
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 420px;
            padding: 0 24px;
            animation: fadeUp 0.6s ease-out;
        }}

        @keyframes fadeUp {{
            from {{
                opacity: 0;
                transform: translateY(16px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .gate-card {{
            background: var(--white);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 48px 40px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
        }}

        .logo {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 28px;
            color: var(--text);
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}

        .logo span {{
            color: var(--coral);
        }}

        .subtitle {{
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 36px;
            line-height: 1.5;
        }}

        .input-group {{
            margin-bottom: 20px;
        }}

        .input-group label {{
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .input-group input {{
            width: 100%;
            padding: 14px 16px;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            border: 1.5px solid var(--border);
            border-radius: 10px;
            background: var(--bg);
            color: var(--text);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .input-group input:focus {{
            border-color: var(--coral);
            box-shadow: 0 0 0 3px var(--coral-light);
        }}

        .input-group input::placeholder {{
            color: #b0b0a8;
        }}

        .error {{
            font-size: 13px;
            color: var(--error);
            margin-bottom: 16px;
            padding: 10px 14px;
            background: #fef2f2;
            border-radius: 8px;
            border: 1px solid #fecaca;
        }}

        button {{
            width: 100%;
            padding: 14px;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            font-weight: 600;
            color: var(--white);
            background: var(--coral);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
        }}

        button:hover {{
            background: var(--coral-hover);
        }}

        button:active {{
            transform: scale(0.98);
        }}

        .footer-note {{
            text-align: center;
            margin-top: 24px;
            font-size: 12px;
            color: var(--text-muted);
        }}

        /* Responsive */
        @media (max-width: 480px) {{
            .gate-card {{
                padding: 36px 28px;
            }}
        }}
    </style>
</head>
<body>
    <div class="bg-circle bg-circle-1"></div>
    <div class="bg-circle bg-circle-2"></div>

    <div class="gate-container">
        <div class="gate-card">
            <div class="logo">Satya<span>Bio</span></div>
            <p class="subtitle">
                This platform is currently in private access.<br>
                Enter the password to continue.
            </p>

            {error_html}

            <form method="POST" action="/_gate/login">
                <div class="input-group">
                    <label>Password</label>
                    <input
                        type="password"
                        name="password"
                        placeholder="Enter access password"
                        autofocus
                        required
                    />
                </div>
                <button type="submit">Enter</button>
            </form>
        </div>
        <p class="footer-note">
            Interested in access? Contact us at
            <a href="mailto:deeya@satyabio.com" style="color: var(--coral); text-decoration: none;">deeya@satyabio.com</a>
        </p>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Middleware class
# ---------------------------------------------------------------------------
class PasswordGateMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every request. If the user doesn't have a valid cookie,
    show them the login page instead of the actual site content.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # --- Allow the login POST endpoint through ---
        if path == "/_gate/login":
            return await self._handle_login(request)

        # --- Check for valid cookie ---
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie and is_valid_cookie(cookie):
            # User is authenticated — let the request through normally
            return await call_next(request)

        # --- No valid cookie — show the login page ---
        return HTMLResponse(get_login_page(), status_code=200)

    async def _handle_login(self, request: Request):
        """Handle the password form submission."""
        form = await request.form()
        password = form.get("password", "")

        if password == GATE_PASSWORD:
            # Correct! Set cookie and redirect to homepage
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(
                key=COOKIE_NAME,
                value=make_cookie_value(),
                max_age=COOKIE_MAX_AGE,
                httponly=True,       # JS can't read the cookie
                samesite="lax",      # basic CSRF protection
                secure=True,         # only sent over HTTPS (Render uses HTTPS)
            )
            return response
        else:
            # Wrong password — show login page with error
            return HTMLResponse(get_login_page(error=True), status_code=200)


# ---------------------------------------------------------------------------
# Easy setup function
# ---------------------------------------------------------------------------
def add_password_gate(app):
    """
    Call this in main.py to add the password gate:

        from auth_gate import add_password_gate
        add_password_gate(app)
    """
    app.add_middleware(PasswordGateMiddleware)
    print("🔒 Password gate is ACTIVE")
