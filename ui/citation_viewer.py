"""
Screen 4: Citation viewer.
Given a turn_id, renders that turn plus a window of surrounding turns
so the user can see the quote in its original conversational context.
"""
import streamlit as st
from models.schemas import AppState


def _find_transcript_for_turn(state: AppState, turn_id: str):
    for t in state.transcripts:
        for turn in t.turns:
            if turn.id == turn_id:
                return t
    return None


def render(state: AppState):
    st.header("Citation Viewer")
    st.caption("Look up any turn ID (e.g. FR-02) to see it in context.")

    all_turn_ids = [turn.id for t in state.transcripts for turn in t.turns]
    turn_id = st.selectbox("Turn ID", options=[""] + all_turn_ids)

    if not turn_id:
        st.info("Select a turn ID to view its surrounding context.")
        return

    transcript = _find_transcript_for_turn(state, turn_id)
    if transcript is None:
        st.error("Source not found.")
        return

    turns = transcript.turns
    idx = next(i for i, t in enumerate(turns) if t.id == turn_id)
    window_start = max(0, idx - 2)
    window_end = min(len(turns), idx + 3)

    st.subheader(f"{transcript.expert_name} — {transcript.country}")
    for t in turns[window_start:window_end]:
        highlight = t.id == turn_id
        prefix = "➡️ " if highlight else "　"
        style_open = "**" if highlight else ""
        st.markdown(f"{prefix}`{t.id}` [{t.timestamp}] {style_open}{t.speaker}: {t.text}{style_open}")