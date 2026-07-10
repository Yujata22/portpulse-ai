import os
import time

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from agent.database import (
    clean_sql,
    execute_read_only_query,
    get_database_schema,
)

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def call_gemini(prompt: str, attempts: int = 3) -> str:
    for attempt in range(1, attempts + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            return response.text.strip()

        except errors.ServerError:
            if attempt == attempts:
                raise

            time.sleep(5 * attempt)


def generate_sql(question: str) -> str:
    schema = get_database_schema()

    prompt = f"""
You are the SQL engine for PortPulse AI, a container logistics
visibility platform.

Convert the user's question into one valid PostgreSQL query.

DATABASE SCHEMA:
{schema}

STRICT RULES:
1. Return SQL only.
2. Do not use Markdown code fences.
3. Use only SELECT statements or CTEs beginning with WITH.
4. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE, COPY, GRANT, REVOKE, CALL, or EXECUTE.
5. Use only tables and columns present in the supplied schema.
6. Add LIMIT 100 unless the query returns an aggregate result.
7. For delayed containers, use the most relevant delay-related
   column or delayed-container view available in the schema.
8. Prefer clear column aliases.
9. Do not invent tables or columns.
10. PostgreSQL syntax only.

USER QUESTION:
{question}
"""

    return clean_sql(call_gemini(prompt))


def summarize_results(
    question: str,
    sql: str,
    results: pd.DataFrame,
) -> str:
    if results.empty:
        return (
            "No matching records were found for this question. "
            "Try broadening the filters or checking the latest event data."
        )

    preview = results.head(20).to_csv(index=False)

    prompt = f"""
You are PortPulse AI, a logistics operations copilot.

Answer the user's question using only the query results below.

USER QUESTION:
{question}

SQL USED:
{sql}

QUERY RESULTS:
{preview}

INSTRUCTIONS:
- Give a concise operational answer.
- Mention the most important finding first.
- Identify risks, delays, carriers, ports, or containers when relevant.
- Give one practical next action.
- Do not claim anything not supported by the data.
- Keep the response below 180 words.
"""

    return call_gemini(prompt)


def answer_question(question: str) -> dict:
    sql = generate_sql(question)
    results = execute_read_only_query(sql)
    summary = summarize_results(question, sql, results)

    return {
        "question": question,
        "sql": sql,
        "results": results,
        "summary": summary,
    }
