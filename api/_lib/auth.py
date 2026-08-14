import os

def is_admin(headers: dict) -> bool:
    admin_key = os.environ.get("ADMIN_API_KEY", "")
    provided = headers.get("X-API-Key") or headers.get("x-api-key") or ""
    return bool(admin_key) and provided == admin_key
 