from http.server import BaseHTTPRequestHandler
import json
import os
import bcrypt


ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "").encode()
ADMIN_SECRET = os.environ.get("ADMIN_SECRET")  


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            password = data.get("password", "").encode()

            if bcrypt.checkpw(password, ADMIN_PASSWORD_HASH):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header(
                    "Set-Cookie",
                    f"admin_secret={ADMIN_SECRET}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=9000"
                )
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            else:
                self._send_json(401, {"success": False, "error": "Wrong password"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})