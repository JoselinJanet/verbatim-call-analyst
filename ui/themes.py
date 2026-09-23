"""Screen 2: Themes and Disagreements."""
import streamlit as st
from models.schemas import AppState

TYPE_LABEL = {
    "contradiction": "🔴 Direct contradiction",
    "emphasis": "🟠 Difference in emphasis",
    "scope": "🔵 Difference in scope",
}


def render(state: AppState):
    st.header("Themes & Disagreements")

    if state.synthesis is None:
        st.info("No synthesis available yet.")
        return

    st.subheader("Common Themes")
    if not state.synthesis.themes:
        st.caption("No cross-expert themes were identified with verifiable evidence.")
    for theme in state.synthesis.themes:
        with st.container(border=True):
            st.markdown(f"**{theme.title}**  \n_Supported by: {', '.join(theme.countries) or '—'}_")
            st.write(theme.description)
            with st.expander(f"{len(theme.supporting_quotes)} supporting quote(s)"):
                for q in theme.supporting_quotes:
                    st.markdown(f"> \"{q.text}\" — {q.country}, `{q.turn_id}` @ **{q.timestamp}**")

    st.subheader("Disagreements")
    if not state.synthesis.disagreements:
        st.caption("No disagreements were identified with verifiable evidence.")
    for dis in state.synthesis.disagreements:
        with st.container(border=True):
            label = TYPE_LABEL.get(dis.type, dis.type)
            if dis.needs_review:
                label += "  ⚠️ flagged for manual review (type unclear)"
            st.markdown(f"**{dis.title}**  \n{label}")
            st.write(dis.description)
            with st.expander(f"{len(dis.quotes_by_country)} quote(s)"):
                for q in dis.quotes_by_country:
                    st.markdown(f"> \"{q.text}\" — {q.country}, `{q.turn_id}` @ **{q.timestamp}**")