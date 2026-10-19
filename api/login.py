"""Admin login + session for the LeicesterCS site.

Design notes:
- Passwords are verified with bcrypt against an env-var hash.
- The session cookie is an HMAC-signed expiry timestamp, NOT the secret.
- Login is rate-limited per IP (best-effort on Vercel; see note below).
- Errors never leak internals to the client.

Required env vars:
    ADMIN_PASSWORD_HASH  bcrypt hash, e.g. "$2b$12$..."
    ADMIN_SECRET         long random string, e.g. `openssl rand -hex 32`

Generate the hash once, locally, then paste it into Vercel:
    python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler

import bcrypt

log = logging.getLogger("leicestercs.admin")

# --- configuration ---------------------------------------------------------

ADMIN_PASSWORD_HASH = (os.environ.get("ADMIN_PASSWORD_HASH") or "").strip().encode()
ADMIN_SECRET = (os.environ.get("ADMIN_SECRET") or "").strip()

SESSION_TTL_SECONDS = 9000          # ~2.5 hours
LOGIN_MAX_ATTEMPTS = 5              # per IP per window
LOGIN_WINDOW_SECONDS = 15 * 60      # 15 minutes
BCRYPT_MAX_PASSWORD_BYTES = 72      # bcrypt silently truncates past this

COOKIE_NAME = "admin_session"

# Best-effort, per-process rate limiting. Resets on cold start; see notes.
_login_attempts: dict[str, list[float]] = {}


# --- session helpers -------------------------------------------------------

def make_session(secret: str, ttl: int = SESSION_TTL_SECONDS) -> str:
    """Return '<expiry>.<hmac>' where hmac = HMAC-SHA256(secret, expiry)."""
    expiry = str(int(time.time()) + ttl)
    sig = hmac.new(secret.encode(), expiry.encode(), hashlib.sha256).hexdigest()
    return f"{expiry}.{sig}"


def verify_session(secret: str, token: str | None) -> bool:
    if not secret or not token or "." not in token:
        return False
    try:
        expiry_str, sig = token.split(".", 1)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        return False
    if expiry <= int(time.time()):
        return False
    expected = hmac.new(secret.encode(), expiry_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# --- rate limiting ---------------------------------------------------------

def _client_ip(handler: BaseHTTPRequestHandler) -> str:
    fwd = handler.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return handler.client_address[0] if handler.client_address else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    cutoff = now - LOGIN_WINDOW_SECONDS
    attempts = [t for t in _login_attempts.get(ip, []) if t > cutoff]
    _login_attempts[ip] = attempts
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        return True
    attempts.append(now)
    return False


# --- handler ---------------------------------------------------------------

class handler(BaseHTTPRequestHandler):
    # Keep the default request logging quiet in serverless logs.
    def log_message(self, fmt, *args):  # noqa: D401
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, payload: dict, extra_headers: dict | None = None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Use this to check an existing session (e.g. to gate /admin.html).
        if self.path.rstrip("/") == "/api/admin/session":
            token = self._read_cookie(COOKIE_NAME)
            self._send_json(200, {"authenticated": verify_session(ADMIN_SECRET, token)})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/admin/login":
            self._send_json(404, {"error": "Not found"})
            return

        # Refuse to operate at all if misconfigured.
        if not ADMIN_SECRET or not ADMIN_PASSWORD_HASH.startswith(b"$2"):
            log.error("admin auth not configured (missing ADMIN_SECRET or ADMIN_PASSWORD_HASH)")
            self._send_json(500, {"error": "Authentication is not configured"})
            return

        ip = _client_ip(self)
        if _rate_limited(ip):
            self._send_json(429, {"error": "Too many attempts. Try again later."})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(400, {"error": "Invalid request"})
            return
        if length <= 0 or length > 4096:
            self._send_json(400, {"error": "Invalid request"})
            return

        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid request"})
            return

        password = data.get("password", "") if isinstance(data, dict) else ""
        if not isinstance(password, str) or not password:
            self._send_json(400, {"error": "Invalid request"})
            return
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
            # bcrypt truncates silently; reject instead of silently matching a prefix.
            self._send_json(401, {"error": "Invalid credentials"})
            return

        try:
            ok = bcrypt.checkpw(password_bytes, ADMIN_PASSWORD_HASH)
        except ValueError:
            # Malformed hash in env, not a user error. Log it, don't leak it.
            log.exception("ADMIN_PASSWORD_HASH is not a valid bcrypt hash")
            self._send_json(500, {"error": "Authentication is not configured"})
            return

        if not ok:
            self._send_json(401, {"error": "Invalid credentials"})
            return

        token = make_session(ADMIN_SECRET)
        cookie = (
            f"{COOKIE_NAME}={token}; "
            f"HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age={SESSION_TTL_SECONDS}"
        )
        log.info("admin login succeeded from %s", ip)
        self._send_json(200, {"success": True}, extra_headers={"Set-Cookie": cookie})

    # -- helpers ------------------------------------------------------------

    def _read_cookie(self, name: str) -> str | None:
        header = self.headers.get("Cookie", "")
        for part in header.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None
