"""
Central configuration for the Transcript Insight app.
Change values here rather than hunting through the codebase.
"""
from pathlib import Path

# ---- Paths ----------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
CACHE_FILE = CACHE_DIR / "cache.json"
PROMPTS_DIR = BASE_DIR / "prompts"

DEFAULT_GUIDE_PATH = DATA_DIR / "Interview_Guide.txt"
DEFAULT_TRANSCRIPT_PATHS = [
    DATA_DIR / "Transcript_1_France.txt",
    DATA_DIR / "Transcript_2_Germany.txt",
    DATA_DIR / "Transcript_3_UK.txt",
]

# ---- LLM (local, llama.cpp) ------------------------------------------------
# Qwen2.5-1.5B-Instruct GGUF, quantized (~1.1GB) - chosen for slower/lower-RAM
# machines. Swap back to the 3B repo below for better judgement quality if
# your laptop can handle it; drop to 0.5B if 1.5B is still too slow.
#
#   3B (best quality, slowest):  repo="Qwen/Qwen2.5-3B-Instruct-GGUF"   file="qwen2.5-3b-instruct-q4_k_m.gguf"
#   1.5B (current, balanced):    repo="Qwen/Qwen2.5-1.5B-Instruct-GGUF" file="qwen2.5-1.5b-instruct-q4_k_m.gguf"
#   0.5B (fastest, lowest RAM):  repo="Qwen/Qwen2.5-0.5B-Instruct-GGUF" file="qwen2.5-0.5b-instruct-q4_k_m.gguf"
#
# Quote accuracy does NOT depend on model size in this app - the model only
# ever selects sentence IDs, never writes quote text (see core/verifier.py).
# A smaller model mainly risks weaker status/disagreement-type judgement,
# which the "flagged for review" / status-downgrade logic already guards.
LLM_REPO_ID = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
LLM_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
LLM_LOCAL_DIR = BASE_DIR / "models_bin"
LLM_N_CTX = 4096
LLM_N_THREADS = 4
LLM_TEMPERATURE = 0.1
LLM_MAX_RETRIES = 3

# ---- Retrieval (Ask feature) ------------------------------------------------
TOP_K_RETRIEVAL = 6
BM25_SCORE_MIN = 0.5  # below this, treat as "not covered"

# ---- Auth (single hardcoded user - see README.md for credentials) ---------
# This is NOT real authentication. There is exactly one hardcoded user,
# meant for one person running this locally - not for exposing the app to
# the internet or supporting multiple real accounts.
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "hasamex2026"

# ---- Chat history persistence ----------------------------------------------
# All of this single user's Ask conversations (across "New Chat" threads)
# are saved here, so closing and reopening the app doesn't lose past chats.
CHAT_HISTORY_FILE = CACHE_DIR / "chat_history.json"

# ---- Auth (single hardcoded user - see README) ------------------------------
# This is a simple access gate, not real multi-user authentication: the app
# runs locally for one person, so one hardcoded username/password is enough.
# Change these before sharing the app with anyone else.
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "hasamex2026"

# ---- Chat history (single user, persisted across sessions) -----------------
CHAT_HISTORY_FILE = CACHE_DIR / "chat_history.json"

# ---- Country code mapping ---------------------------------------------------
COUNTRY_CODES = {
    "France": "FR",
    "Germany": "DE",
    "United Kingdom": "UK",
    "UK": "UK",
}

STATUS_VALUES = ("answered", "partial", "not_discussed")
DISAGREEMENT_TYPES = ("contradiction", "emphasis", "scope")