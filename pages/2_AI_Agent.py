import streamlit as st

from agent.sql_agent import answer_question

st.set_page_config(
    page_title="PortPulse AI Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 PortPulse AI Agent")
st.caption(
    "Ask questions about containers, delays, carriers, ports, "
    "and logistics risks using natural language."
)

example_questions = [
    "Which containers are currently delayed?",
    "Which carrier has the highest average delay?",
    "Which ports have the most delayed containers?",
    "Show the latest status of 10 containers.",
    "Which containers require immediate attention?",
]

selected_example = st.selectbox(
    "Example questions",
    ["Select a question"] + example_questions,
)

default_question = (
    selected_example if selected_example != "Select a question" else ""
)

question = st.text_input(
    "Ask PortPulse AI",
    value=default_question,
    placeholder="Example: Which ports have the highest average delay?",
)

if st.button("Analyze logistics data", type="primary"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            with st.spinner(
                "Generating SQL and analyzing container data..."
            ):
                response = answer_question(question.strip())

            st.subheader("Operational insight")
            st.info(response["summary"])

            col1, col2 = st.columns([1, 2])

            with col1:
                st.metric(
                    "Rows returned",
                    len(response["results"]),
                )

            with col2:
                st.caption(
                    "Gemini-generated query executed against "
                    "PostgreSQL in read-only mode."
                )

            with st.expander("View generated PostgreSQL"):
                st.code(response["sql"], language="sql")

            st.subheader("Supporting data")

            if response["results"].empty:
                st.warning("No matching records were found.")
            else:
                st.dataframe(
                    response["results"],
                    use_container_width=True,
                    hide_index=True,
                )

        except Exception as exc:
            st.error("The agent could not complete this request.")
            st.exception(exc)
