import streamlit as st

from agent.sql_agent import answer_question

st.set_page_config(
    page_title="PortPulse AI Agent",
    page_icon="🚢",
    layout="wide",
)

st.title("🚢 PortPulse AI Agent")
st.caption(
    "Ask natural-language questions about container movements, "
    "delays, carriers, ports, and operational risks."
)

example_questions = [
    "Which containers are currently delayed?",
    "Which carrier has the highest average delay?",
    "Which ports have the most delayed containers?",
    "Show the latest status of 10 containers.",
    "Which delayed containers require immediate attention?",
]

with st.sidebar:
    st.header("Example questions")

    for question in example_questions:
        st.write(f"• {question}")

question = st.text_input(
    "Ask PortPulse AI",
    placeholder="Example: Which ports have the highest average delay?",
)

ask_button = st.button(
    "Analyze",
    type="primary",
    use_container_width=True,
)

if ask_button:
    if not question.strip():
        st.warning("Enter a logistics question first.")
    else:
        try:
            with st.spinner(
                "Generating SQL and analyzing logistics data..."
            ):
                response = answer_question(question.strip())

            st.subheader("Operational insight")
            st.success(response["summary"])

            with st.expander("Generated PostgreSQL query"):
                st.code(response["sql"], language="sql")

            st.subheader("Query results")

            if response["results"].empty:
                st.info("The query returned no records.")
            else:
                st.dataframe(
                    response["results"],
                    use_container_width=True,
                    hide_index=True,
                )

        except Exception as exc:
            st.error("PortPulse AI could not complete the request.")
            st.exception(exc)

st.divider()

st.caption(
    "Gemini-powered natural-language analytics with validated, "
    "read-only PostgreSQL execution."
)
