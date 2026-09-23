"""
Minimal single-user login gate.

This is intentionally NOT real authentication - there is exactly one
hardcoded username/password pair (see README.md), meant for a single
person running this app locally. It exists to put a login screen in
front of the app and to have a stable identity to attach chat history
to, not to secure the app against real unauthorized access.
"""
from config import AUTH_USERNAME, AUTH_PASSWORD


def check_credentials(username: str, password: str) -> bool:
    return username == AUTH_USERNAME and password == AUTH_PASSWORD