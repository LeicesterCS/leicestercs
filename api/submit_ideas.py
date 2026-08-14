from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
import hashlib
import urllib.request
from datetime import datetime, timezone
from supabase import create_client

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DAILY_LIMIT = 5  # max idea submissions per identifier per day


def get_cookie(headers, name):
    cookie_header = headers.get("Cookie", "")
    cookies = dict(
        item.strip().split("=", 1)
        for item in cookie_header.split(";")
        if "=" in item
    )
    return cookies.get(name)


def get_client_ip_hash(headers):
    forwarded = headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()


def check_and_increment(identifier):
    """Returns True if allowed, False if over the daily limit."""
    now = datetime.now(timezone.utc)
    result = (
        supabase.table("idea_rate_limits")
        .select("*")
        .eq("identifier", identifier)
        .execute()
    )

    if not result.data:
        supabase.table("idea_rate_limits").insert(
            {"identifier": identifier, "count": 1}
        ).execute()
        return True

    row = result.data[0]
    reset_at = datetime.fromisoformat(row["reset_at"])

    if now > reset_at:
        supabase.table("idea_rate_limits").update(
            {"count": 1, "reset_at": (now.isoformat())}
        ).eq("identifier", identifier).execute()
        return True

    if row["count"] >= DAILY_LIMIT:
        return False

    supabase.table("idea_rate_limits").update(
        {"count": row["count"] + 1}
    ).eq("identifier", identifier).execute()
    return True


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        try:
            cookie_id = get_cookie(self.headers, "idea_client_id")
            new_cookie = None
            if not cookie_id:
                cookie_id = str(uuid.uuid4())
                new_cookie = cookie_id

            ip_hash = get_client_ip_hash(self.headers)

            if not check_and_increment(f"cookie:{cookie_id}"):
                self._send_json(429, {"error": "Daily suggestion limit reached"})
                return

            if not check_and_increment(f"ip:{ip_hash}"):
                self._send_json(429, {"error": "Daily suggestion limit reached"})
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            idea = data.get("idea", "").strip()
            name = data.get("name", "Anonymous").strip()

            if not idea:
                self._send_json(400, {"error": "Idea text is required"})
                return

            if len(idea) > 1000:
                self._send_json(400, {"error": "Idea is too long"})
                return

            discord_payload = {
                "embeds": [
                    {
                        "title": "New Idea Suggestion",
                        "description": idea,
                        "footer": {"text": f"Submitted by: {name}"},
                        "color": 5814783,
                    }
                ]
            }

            req = urllib.request.Request(
                DISCORD_WEBHOOK_URL,
                data=json.dumps(discord_payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if new_cookie:
                self.send_header(
                    "Set-Cookie",
                    f"idea_client_id={new_cookie}; Secure; SameSite=Strict; Path=/; Max-Age=31536000",
                )
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        except Exception as e:
            self._send_json(500, {"error": str(e)})