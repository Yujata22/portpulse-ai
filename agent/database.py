import os
import re

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Force values from .env to replace stale terminal variables.
load_dotenv(override=True)


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from the .env file.")

    return psycopg2.connect(
        database_url,
        connect_timeout=10,
    )


def get_database_schema() -> str:
    query = """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """

    with get_connection() as connection:
        schema_df = pd.read_sql_query(query, connection)

    if schema_df.empty:
        return "No tables were found in the public schema."

    schema_lines = []

    for table_name, columns in schema_df.groupby("table_name"):
        schema_lines.append(f"\nTABLE: {table_name}")

        for _, row in columns.iterrows():
            schema_lines.append(
                f"- {row['column_name']} ({row['data_type']})"
            )

    return "\n".join(schema_lines)


def clean_sql(sql: str) -> str:
    sql = sql.strip()

    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s*```$", "", sql)

    return sql.strip().rstrip(";")


def validate_read_only_sql(sql: str) -> None:
    normalized = re.sub(r"\s+", " ", sql.strip()).lower()

    if not normalized.startswith(("select ", "with ")):
        raise ValueError("Only read-only SELECT queries are permitted.")

    forbidden_operations = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "call",
        "execute",
    ]

    for operation in forbidden_operations:
        if re.search(rf"\b{operation}\b", normalized):
            raise ValueError(
                f"Blocked SQL operation detected: {operation.upper()}"
            )

    if ";" in sql:
        raise ValueError("Multiple SQL statements are not allowed.")


def execute_read_only_query(sql: str) -> pd.DataFrame:
    cleaned_sql = clean_sql(sql)
    validate_read_only_sql(cleaned_sql)

    with get_connection() as connection:
        connection.set_session(readonly=True, autocommit=False)

        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '10s';")

        return pd.read_sql_query(cleaned_sql, connection)


