"""
Persists chat conversations for the single app user across sessions and
restarts. Conversations are stored as a list of independent threads, each
with its own id, auto-generated title, and message list - this is what
makes "New Chat" possible (start a fresh thread) without losing earlier
ones, and what makes history survive closing/reopening the app.

Storage is a single JSON file (see config.CHAT_HISTORY_FILE), consistent
with the rest of the app's "no database needed at this scale" approach.
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from config import CHAT_HISTORY_FILE

TITLE_MAX_LEN = 42


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_conversations() -> List[Dict]:
    if not CHAT_HISTORY_FILE.exists():
        return []
    try:
        return json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []  # corrupt file -> start fresh rather than crash the app


def save_conversations(conversations: List[Dict]) -> None:
    CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHAT_HISTORY_FILE.write_text(json.dumps(conversations, indent=2), encoding="utf-8")


def new_conversation() -> Dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "title": "New chat",
        "created_at": _now_iso(),
        "messages": [],  # each: {"role": "user"|"assistant", "content": str}
    }


def find_conversation(conversations: List[Dict], conv_id: str) -> Optional[Dict]:
    return next((c for c in conversations if c["id"] == conv_id), None)


def add_message(conv: Dict, role: str, content: str) -> None:
    """
    Appends a message to a conversation in place, and auto-titles the
    conversation from the first user message if it's still "New chat".
    """
    conv["messages"].append({"role": role, "content": content})
    if role == "user" and conv["title"] == "New chat":
        title = content.strip().replace("\n", " ")
        conv["title"] = (title[:TITLE_MAX_LEN] + "…") if len(title) > TITLE_MAX_LEN else title