import os
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urlparse

import psycopg2
from airflow.sdk import dag, task


CONNECTION_ENV_NAME = "AIRFLOW_CONN_CONTAINERPULSE_POSTGRES"


def get_database_connection():
    """
    Create a PostgreSQL connection using the connection URI
    configured in docker-compose-airflow.yml.
    """

    connection_uri = os.getenv(CONNECTION_ENV_NAME)

    if not connection_uri:
        raise RuntimeError(
            f"Environment variable {CONNECTION_ENV_NAME} is missing."
        )

    parsed_uri = urlparse(connection_uri)

    return psycopg2.connect(
        host=parsed_uri.hostname,
        port=parsed_uri.port or 5432,
        database=parsed_uri.path.lstrip("/"),
        user=parsed_uri.username,
        password=parsed_uri.password,
        connect_timeout=10,
    )


@dag(
    dag_id="portpulse_daily_pipeline",
    description=(
        "Validate PortPulse container events and build "
        "daily port-level operational metrics."
    ),
    schedule="0 6 * * *",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=[
        "portpulse",
        "logistics",
        "postgresql",
        "data-quality",
    ],
)
def portpulse_daily_pipeline():

    @task
    def check_database_connection() -> Dict[str, Any]:
        """
        Confirm that Airflow can reach the PortPulse database.
        """

        connection = get_database_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        current_database(),
                        current_user,
                        NOW();
                    """
                )

                database_name, database_user, checked_at = (
                    cursor.fetchone()
                )

            result = {
                "status": "connected",
                "database": database_name,
                "user": database_user,
                "checked_at": checked_at.isoformat(),
            }

            print("Database connection successful")
            print(result)

            return result

        finally:
            connection.close()

    @task
    def validate_tracking_events() -> Dict[str, Any]:
        """
        Run fundamental data-quality checks against tracking_events.
        """

        connection = get_database_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total_events,
                        COUNT(DISTINCT event_id)
                            AS unique_event_ids,
                        COUNT(DISTINCT container_number)
                            AS unique_containers,
                        COUNT(*) FILTER (
                            WHERE container_number IS NULL
                        ) AS missing_container_numbers,
                        COUNT(*) FILTER (
                            WHERE milestone IS NULL
                        ) AS missing_milestones,
                        COUNT(*) FILTER (
                            WHERE event_timestamp IS NULL
                        ) AS missing_event_timestamps,
                        COUNT(*) FILTER (
                            WHERE delay_hours < 0
                        ) AS invalid_negative_delays
                    FROM tracking_events;
                    """
                )

                (
                    total_events,
                    unique_event_ids,
                    unique_containers,
                    missing_container_numbers,
                    missing_milestones,
                    missing_event_timestamps,
                    invalid_negative_delays,
                ) = cursor.fetchone()

            if total_events == 0:
                raise ValueError(
                    "Data-quality check failed: tracking_events is empty."
                )

            if total_events != unique_event_ids:
                raise ValueError(
                    "Data-quality check failed: duplicate event IDs found."
                )

            if missing_container_numbers > 0:
                raise ValueError(
                    "Data-quality check failed: missing container numbers."
                )

            if missing_milestones > 0:
                raise ValueError(
                    "Data-quality check failed: missing milestones."
                )

            if missing_event_timestamps > 0:
                raise ValueError(
                    "Data-quality check failed: "
                    "missing event timestamps."
                )

            if invalid_negative_delays > 0:
                raise ValueError(
                    "Data-quality check failed: negative delays found."
                )

            result = {
                "status": "passed",
                "total_events": total_events,
                "unique_event_ids": unique_event_ids,
                "unique_containers": unique_containers,
                "missing_container_numbers": (
                    missing_container_numbers
                ),
                "missing_milestones": missing_milestones,
                "missing_event_timestamps": (
                    missing_event_timestamps
                ),
                "invalid_negative_delays": (
                    invalid_negative_delays
                ),
            }

            print("All tracking-event quality checks passed")
            print(result)

            return result

        finally:
            connection.close()

    @task
    def build_daily_port_metrics() -> Dict[str, Any]:
        """
        Create and refresh a daily port-level metrics table.
        """

        connection = get_database_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_port_metrics (
                        metric_date DATE NOT NULL,
                        port_of_discharge TEXT NOT NULL,
                        total_events INTEGER NOT NULL,
                        total_containers INTEGER NOT NULL,
                        delayed_containers INTEGER NOT NULL,
                        average_delay_hours NUMERIC(10, 2)
                            NOT NULL,
                        maximum_delay_hours INTEGER NOT NULL,
                        calculated_at TIMESTAMPTZ
                            NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (
                            metric_date,
                            port_of_discharge
                        )
                    );
                    """
                )

                cursor.execute(
                    """
                    INSERT INTO daily_port_metrics (
                        metric_date,
                        port_of_discharge,
                        total_events,
                        total_containers,
                        delayed_containers,
                        average_delay_hours,
                        maximum_delay_hours,
                        calculated_at
                    )
                    SELECT
                        event_timestamp::DATE AS metric_date,
                        port_of_discharge,
                        COUNT(*) AS total_events,
                        COUNT(
                            DISTINCT container_number
                        ) AS total_containers,
                        COUNT(
                            DISTINCT container_number
                        ) FILTER (
                            WHERE is_delayed = TRUE
                        ) AS delayed_containers,
                        COALESCE(
                            ROUND(
                                AVG(delay_hours) FILTER (
                                    WHERE is_delayed = TRUE
                                ),
                                2
                            ),
                            0
                        ) AS average_delay_hours,
                        COALESCE(
                            MAX(delay_hours),
                            0
                        ) AS maximum_delay_hours,
                        CURRENT_TIMESTAMP
                    FROM tracking_events
                    GROUP BY
                        event_timestamp::DATE,
                        port_of_discharge
                    ON CONFLICT (
                        metric_date,
                        port_of_discharge
                    )
                    DO UPDATE SET
                        total_events = EXCLUDED.total_events,
                        total_containers = EXCLUDED.total_containers,
                        delayed_containers = (
                            EXCLUDED.delayed_containers
                        ),
                        average_delay_hours = (
                            EXCLUDED.average_delay_hours
                        ),
                        maximum_delay_hours = (
                            EXCLUDED.maximum_delay_hours
                        ),
                        calculated_at = CURRENT_TIMESTAMP;
                    """
                )

                affected_rows = cursor.rowcount

            connection.commit()

            result = {
                "status": "completed",
                "rows_inserted_or_updated": affected_rows,
            }

            print("Daily port metrics successfully refreshed")
            print(result)

            return result

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @task
    def verify_daily_metrics() -> Dict[str, Any]:
        """
        Verify that the daily metrics table contains valid results.
        """

        connection = get_database_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS metric_rows,
                        COUNT(DISTINCT metric_date)
                            AS metric_dates,
                        COUNT(DISTINCT port_of_discharge)
                            AS active_ports,
                        MAX(calculated_at)
                            AS latest_calculation
                    FROM daily_port_metrics;
                    """
                )

                (
                    metric_rows,
                    metric_dates,
                    active_ports,
                    latest_calculation,
                ) = cursor.fetchone()

            if metric_rows == 0:
                raise ValueError(
                    "Metrics verification failed: "
                    "daily_port_metrics is empty."
                )

            result = {
                "status": "verified",
                "metric_rows": metric_rows,
                "metric_dates": metric_dates,
                "active_ports": active_ports,
                "latest_calculation": (
                    latest_calculation.isoformat()
                    if latest_calculation
                    else None
                ),
            }

            print("Daily metrics verification passed")
            print(result)

            return result

        finally:
            connection.close()

    database_check = check_database_connection()
    quality_check = validate_tracking_events()
    metrics_build = build_daily_port_metrics()
    metrics_verification = verify_daily_metrics()

    (
        database_check
        >> quality_check
        >> metrics_build
        >> metrics_verification
    )


portpulse_daily_pipeline()