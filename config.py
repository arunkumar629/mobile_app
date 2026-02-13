"""
SATHI 2026 Configuration
Password is read from this file first. If empty/missing, falls back to
environment variable SATHI_PASSWORD. If that's also missing, no auth is used.
"""
import os

# ── Authentication ──
# Set password here. If blank, checks environment variable SATHI_PASSWORD.
PASSWORD = "sathi2026"

def get_password():
    """Returns the active password, or None if auth is disabled."""
    pw = PASSWORD.strip() if PASSWORD else None
    if not pw:
        pw = os.environ.get("SATHI_PASSWORD", "").strip() or None
    return pw

# ── Application ──
SECRET_KEY = "sathi-2026-vision-aid-key"
DB_NAME = "sathi.db"
PER_PAGE = 20
