
from functools import wraps
from pathlib import Path
import tempfile
import traceback
from typing import Optional

from flask import Flask, jsonify, request, session, render_template
from flask_cors import CORS

from config import (
    DEFAULT_GUIDE_PATH,
    DEFAULT_TRANSCRIPT_PATHS,
    AUTH_USERNAME,
    AUTH_PASSWORD,
)
from core.auth import check_credentials
from core.cache import load_cache, clear_cache, save_cache
from core.pipeline import run_pipeline
from core.relevance import IrrelevantContentError
from core.retrieval import BM25Index, answer_question
from core.parser import sentence_lookup
from core import chat_store
from models.schemas import AppState

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "verbatim-call-analyst-secret-key-production-local"
CORS(app, supports_credentials=True)

_current_state: Optional[AppState] = None
_bm25_index: Optional[BM25Index] = None
_sentence_lookup: Optional[dict] = None


def get_state(force_reload: bool = False) -> AppState:
    global _current_state, _bm25_index, _sentence_lookup

    if _current_state is None or force_reload:
        state = load_cache()
        if state is None:
            state = run_pipeline(DEFAULT_GUIDE_PATH, DEFAULT_TRANSCRIPT_PATHS)
        _current_state = state
        _bm25_index = BM25Index(state.transcripts)
        _sentence_lookup = sentence_lookup(state.transcripts)

    return _current_state


def get_retrieval_components():
    """Ensure state and retrieval index are initialized."""
    state = get_state()
    global _bm25_index, _sentence_lookup
    if _bm25_index is None:
        _bm25_index = BM25Index(state.transcripts)
    if _sentence_lookup is None:
        _sentence_lookup = sentence_lookup(state.transcripts)
    return state, _bm25_index, _sentence_lookup


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated", False):
            return jsonify({"error": "Unauthorized", "authenticated": False}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    return jsonify({
        "authenticated": session.get("authenticated", False),
        "username": session.get("username", None),
    })


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if check_credentials(username, password):
        session["authenticated"] = True
        session["username"] = username
        return jsonify({
            "success": True,
            "authenticated": True,
            "username": username,
            "message": "Login successful",
        })

    return jsonify({
        "success": False,
        "authenticated": False,
        "error": "Invalid username or password.",
    }), 401


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True, "authenticated": False})


@app.route("/api/state", methods=["GET"])
@login_required
def api_state():
    try:
        state = get_state()
        countries = sorted(list({c.country for c in state.answer_grid}))

        experts = [
            {
                "country": t.country,
                "country_code": t.country_code,
                "expert_name": t.expert_name,
                "expert_role": t.expert_role,
                "call": t.call,
                "turn_count": len(t.turns),
            }
            for t in state.transcripts
        ]

        payload = {
            "guide_questions": [q.model_dump() for q in state.guide_questions],
            "countries": countries,
            "answer_grid": [cell.model_dump() for cell in state.answer_grid],
            "synthesis": state.synthesis.model_dump() if state.synthesis else None,
            "experts": experts,
            "all_turn_ids": [turn.id for t in state.transcripts for turn in t.turns],
        }
        return jsonify(payload)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to load application state: {str(e)}"}), 500


@app.route("/api/pipeline/run", methods=["POST"])
@login_required
def api_pipeline_run():
    global _current_state, _bm25_index, _sentence_lookup
    try:
        force_regenerate = request.form.get("force_regenerate", "false").lower() == "true"
        guide_file = request.files.get("guide_file")
        transcript_files = request.files.getlist("transcript_files")

        guide_path = DEFAULT_GUIDE_PATH
        if guide_file and guide_file.filename:
            suffix = Path(guide_file.filename).suffix
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            guide_file.save(tmp.name)
            guide_path = Path(tmp.name)

        transcript_paths = DEFAULT_TRANSCRIPT_PATHS
        if transcript_files and len(transcript_files) > 0 and transcript_files[0].filename:
            transcript_paths = []
            for tf in transcript_files:
                if tf.filename:
                    suffix = Path(tf.filename).suffix
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tf.save(tmp.name)
                    transcript_paths.append(Path(tmp.name))

        state = run_pipeline(guide_path, transcript_paths, force_regenerate=force_regenerate)
        _current_state = state
        _bm25_index = BM25Index(state.transcripts)
        _sentence_lookup = sentence_lookup(state.transcripts)

        return jsonify({
            "success": True,
            "message": "Pipeline completed successfully",
        })
    except IrrelevantContentError as e:
        return jsonify({
            "error": "Irrelevant Content",
            "message": f"Uploaded transcripts do not appear to match this guide: {str(e)}",
        }), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Pipeline execution failed: {str(e)}"}), 500


@app.route("/api/cache/clear", methods=["POST"])
@login_required
def api_cache_clear():
    global _current_state, _bm25_index, _sentence_lookup
    try:
        clear_cache()
        _current_state = None
        _bm25_index = None
        _sentence_lookup = None
        return jsonify({"success": True, "message": "Cache successfully cleared."})
    except Exception as e:
        return jsonify({"error": f"Failed to clear cache: {str(e)}"}), 500


@app.route("/api/chat/conversations", methods=["GET"])
@login_required
def get_conversations():
    conversations = chat_store.load_conversations()
    if not conversations:
        first = chat_store.new_conversation()
        conversations.append(first)
        chat_store.save_conversations(conversations)
    return jsonify(conversations)


@app.route("/api/chat/conversations", methods=["POST"])
@login_required
def create_conversation():
    conversations = chat_store.load_conversations()
    conv = chat_store.new_conversation()
    conversations.append(conv)
    chat_store.save_conversations(conversations)
    return jsonify(conv)


@app.route("/api/chat/conversations/<conv_id>", methods=["GET"])
@login_required
def get_conversation(conv_id):
    conversations = chat_store.load_conversations()
    conv = chat_store.find_conversation(conversations, conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify(conv)


@app.route("/api/chat/conversations/<conv_id>", methods=["DELETE"])
@login_required
def delete_conversation(conv_id):
    conversations = chat_store.load_conversations()
    conversations = [c for c in conversations if c["id"] != conv_id]
    if not conversations:
        conversations.append(chat_store.new_conversation())
    chat_store.save_conversations(conversations)
    return jsonify({"success": True, "conversations": conversations})


@app.route("/api/chat/ask", methods=["POST"])
@login_required
def chat_ask():
    data = request.get_json(silent=True) or {}
    conv_id = data.get("conv_id")
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    conversations = chat_store.load_conversations()
    if not conversations:
        conv = chat_store.new_conversation()
        conversations.append(conv)
        conv_id = conv["id"]

    conv = chat_store.find_conversation(conversations, conv_id) if conv_id else conversations[-1]
    if not conv:
        conv = chat_store.new_conversation()
        conversations.append(conv)

    chat_store.add_message(conv, "user", question)

    state, bm25_index, lookup = get_retrieval_components()
    result = answer_question(question, bm25_index, state.transcripts, lookup)

    if result.covered and result.citations:
        citation_str = ", ".join(f"[{q.country} {q.turn_id} @ {q.timestamp}]" for q in result.citations)
        answer_text = f"{result.answer}\n\n*Verified Sources:* {citation_str}"
    else:
        answer_text = result.answer

    chat_store.add_message(conv, "assistant", answer_text)
    chat_store.save_conversations(conversations)

    return jsonify({
        "success": True,
        "answer": answer_text,
        "covered": result.covered,
        "citations": [q.model_dump() for q in result.citations],
        "conversation": conv,
    })


@app.route("/api/citations/turn/<turn_id>", methods=["GET"])
@login_required
def get_citation_turn(turn_id):
    state = get_state()
    target_transcript = None
    target_turn = None
    turn_index = -1

    for t in state.transcripts:
        for idx, turn in enumerate(t.turns):
            if turn.id == turn_id:
                target_transcript = t
                target_turn = turn
                turn_index = idx
                break
        if target_transcript:
            break

    if not target_transcript or target_turn is None:
        return jsonify({"error": f"Turn '{turn_id}' not found."}), 404

    turns = target_transcript.turns
    window_start = max(0, turn_index - 3)
    window_end = min(len(turns), turn_index + 4)

    context_turns = [t.model_dump() for t in turns[window_start:window_end]]

    return jsonify({
        "target_turn_id": turn_id,
        "country": target_transcript.country,
        "country_code": target_transcript.country_code,
        "expert_name": target_transcript.expert_name,
        "expert_role": target_transcript.expert_role,
        "call": target_transcript.call,
        "target_turn": target_turn.model_dump(),
        "context_turns": context_turns,
        "window_start_idx": window_start,
        "total_turns": len(turns),
    })


@app.route("/api/transcripts", methods=["GET"])
@login_required
def get_transcripts():
    state = get_state()
    return jsonify([
        {
            "country": t.country,
            "country_code": t.country_code,
            "expert_name": t.expert_name,
            "expert_role": t.expert_role,
            "call": t.call,
            "turns": [turn.model_dump() for turn in t.turns],
        }
        for t in state.transcripts
    ])


if __name__ == "__main__":
    print("Pre-warming Transcript Insight pipeline / cache...")
    get_state()
    print("Transcript Insight ready. Serving on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)