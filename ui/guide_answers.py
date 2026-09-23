"""Screen 1: Guide Answers - a grid of 6 questions x 3 experts."""
import streamlit as st
from models.schemas import AppState

STATUS_BADGE = {
    "answered": "🟢 Answered",
    "partial": "🟡 Partial",
    "not_discussed": "⚪ Not discussed",
}


def render(state: AppState):
    st.header("Guide Answers")
    st.caption("Each cell shows the expert's answer, a status, and verified verbatim quotes.")

    questions = {q.number: q for q in state.guide_questions}
    countries = sorted({c.country for c in state.answer_grid})

    for q_num in sorted(questions.keys()):
        question = questions[q_num]
        st.subheader(f"Q{q_num}. {question.text}")
        cols = st.columns(len(countries))

        for col, country in zip(cols, countries):
            cell = next(
                (c for c in state.answer_grid if c.question_number == q_num and c.country == country),
                None,
            )
            with col:
                st.markdown(f"**{country}**")
                if cell is None:
                    st.info("No data")
                    continue

                if cell.generation_failed:
                    st.warning("Generation failed - flagged for review")
                    continue

                st.write(STATUS_BADGE.get(cell.status, cell.status))
                st.write(cell.short_answer)

                if cell.quotes:
                    with st.expander(f"{len(cell.quotes)} verified quote(s)"):
                        for q in cell.quotes:
                            st.markdown(
                                f"> \"{q.text}\"\n\n"
                                f"— {q.country}, `{q.turn_id}` @ **{q.timestamp}** "
                                f"{'✅ verified' if q.verified else ''}"
                            )
                else:
                    st.caption("No quotable evidence found.")
        st.divider()