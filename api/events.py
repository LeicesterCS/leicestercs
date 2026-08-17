from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def is_admin(headers):
    cookie_header = headers.get("Cookie", "")
    cookies = dict(
        item.strip().split("=", 1)
        for item in cookie_header.split(";")
        if "=" in item
    )
    return cookies.get("admin_secret") == ADMIN_SECRET


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _get_id_param(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        return qs.get("id", [None])[0]

    def do_GET(self):
        try:
            result = (
                supabase.table("events")
                .select("*")
                .order("event_date", desc=False)
                .execute()
            )
            self._send_json(200, result.data)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_POST(self):
        if not is_admin(self.headers):
            self._send_json(401, {"error": "Not authorized"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            required = ["title", "event_date"]
            missing = [f for f in required if f not in data]
            if missing:
                self._send_json(400, {"error": f"Missing fields: {', '.join(missing)}"})
                return

            new_event = {
                "title": data.get("title"),
                "description": data.get("description"),
                "event_date": data.get("event_date"),
                "event_end_date": data.get("event_end_date") or None,
                "event_time": data.get("event_time") or None,
                "location": data.get("location"),
                "action_link": data.get("action_link") or None,
                "action_label": data.get("action_label") or None,
            }

            result = supabase.table("events").insert(new_event).execute()
            self._send_json(201, result.data)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_PUT(self):
        if not is_admin(self.headers):
            self._send_json(401, {"error": "Not authorized"})
            return

        event_id = self._get_id_param()
        if not event_id:
            self._send_json(400, {"error": "Missing event id"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            updated_event = {
                "title": data.get("title"),
                "description": data.get("description"),
                "event_date": data.get("event_date"),
                "event_end_date": data.get("event_end_date") or None,
                "event_time": data.get("event_time") or None,
                "location": data.get("location"),
                "action_link": data.get("action_link") or None,
                "action_label": data.get("action_label") or None,
            }

            result = (
                supabase.table("events")
                .update(updated_event)
                .eq("id", event_id)
                .execute()
            )
            self._send_json(200, result.data)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_DELETE(self):
        if not is_admin(self.headers):
            self._send_json(401, {"error": "Not authorized"})
            return

        event_id = self._get_id_param()
        if not event_id:
            self._send_json(400, {"error": "Missing event id"})
            return

        try:
            result = (
                supabase.table("events")
                .delete()
                .eq("id", event_id)
                .execute()
            )
            self._send_json(200, {"success": True})
        except Exception as e:
            self._send_json(500, {"error": str(e)})