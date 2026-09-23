"""
Screen 3: Ask - free-form Q&A over all transcripts, with citations.

Supports multiple saved conversation threads for the single app user:
a "+ New chat" button starts a fresh thread without deleting earlier
ones, and every thread is persisted to disk (core/chat_store.py) so
history survives closing and reopening the app.
"""
import streamlit as st
from models.schemas import AppState
from core.retrieval import BM25Index, answer_question
from core.parser import sentence_lookup
from core import chat_store


def _ensure_state(state: AppState):
    if "bm25_index" not in st.session_state:
        st.session_state.bm25_index = BM25Index(state.transcripts)
    if "sentence_lookup" not in st.session_state:
        st.session_state.sentence_lookup = sentence_lookup(state.transcripts)
    if "conversations" not in st.session_state:
        st.session_state.conversations = chat_store.load_conversations()
        if not st.session_state.conversations:
            first = chat_store.new_conversation()
            st.session_state.conversations.append(first)
            chat_store.save_conversations(st.session_state.conversations)
        st.session_state.active_conv_id = st.session_state.conversations[-1]["id"]


def render(state: AppState):
    st.header("Ask")
    st.caption('Answers come only from the transcripts. Unsupported questions get "Not covered in these calls."')

    _ensure_state(state)

    col_history, col_chat = st.columns([1, 3], gap="medium")

    with col_history:
        if st.button("➕ New chat", use_container_width=True, type="primary"):
            conv = chat_store.new_conversation()
            st.session_state.conversations.append(conv)
            st.session_state.active_conv_id = conv["id"]
            chat_store.save_conversations(st.session_state.conversations)
            st.rerun()

        st.caption("History")
        for conv in reversed(st.session_state.conversations):
            is_active = conv["id"] == st.session_state.active_conv_id
            label = f"{'🟢' if is_active else '💬'} {conv['title']}"
            if st.button(label, key=f"conv_btn_{conv['id']}", use_container_width=True):
                st.session_state.active_conv_id = conv["id"]
                st.rerun()

    active_conv = chat_store.find_conversation(st.session_state.conversations, st.session_state.active_conv_id)

    with col_chat:
        with st.container(height=420, border=True):
            if not active_conv["messages"]:
                st.caption("Ask anything about the interviews to start this chat.")
            for msg in active_conv["messages"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        question = st.chat_input("Ask a question about the interviews...")
        if question:
            chat_store.add_message(active_conv, "user", question)

            with st.spinner("Searching transcripts..."):
                result = answer_question(
                    question,
                    st.session_state.bm25_index,
                    state.transcripts,
                    st.session_state.sentence_lookup,
                )

            if result.covered and result.citations:
                citation_str = ", ".join(f"[{q.country} {q.timestamp}]" for q in result.citations)
                answer_text = f"{result.answer}\n\n_{citation_str}_"
            else:
                answer_text = result.answer

            chat_store.add_message(active_conv, "assistant", answer_text)
            chat_store.save_conversations(st.session_state.conversations)
            st.rerun()