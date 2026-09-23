from pathlib import Path

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

LLM_REPO_ID = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
LLM_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
LLM_LOCAL_DIR = BASE_DIR / "models_bin"
LLM_N_CTX = 4096
LLM_N_THREADS = 4
LLM_TEMPERATURE = 0.1
LLM_MAX_RETRIES = 3

TOP_K_RETRIEVAL = 6
BM25_SCORE_MIN = 0.5

AUTH_USERNAME = "admin"
AUTH_PASSWORD = "hasamex2026"

CHAT_HISTORY_FILE = CACHE_DIR / "chat_history.json"

COUNTRY_CODES = {
    "France": "FR",
    "Germany": "DE",
    "United Kingdom": "UK",
    "UK": "UK",
}

STATUS_VALUES = ("answered", "partial", "not_discussed")
DISAGREEMENT_TYPES = ("contradiction", "emphasis", "scope")