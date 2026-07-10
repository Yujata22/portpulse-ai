import json

import psycopg2
from kafka import KafkaConsumer


TOPIC_NAME = "container-tracking-events"
BOOTSTRAP_SERVERS = "localhost:9092"


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="containerpulse",
        user="containerpulse",
        password="containerpulse",
    )


consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="containerpulse-db-consumer",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)


conn = get_connection()
cursor = conn.cursor()

print("Listening for Kafka events...")

for message in consumer:
    event = message.value

    try:
        cursor.execute(
            """
            INSERT INTO tracking_events (
                event_id,
                container_number,
                carrier,
                milestone,
                location,
                origin,
                port_of_discharge,
                destination,
                planned_timestamp,
                event_timestamp,
                is_delayed,
                delay_hours,
                kafka_partition,
                kafka_offset
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s
            )
            ON CONFLICT (event_id) DO NOTHING
            """,
            (
                event["event_id"],
                event["container_number"],
                event["carrier"],
                event["milestone"],
                event["location"],
                event["origin"],
                event["port_of_discharge"],
                event["destination"],
                event["planned_timestamp"],
                event["event_timestamp"],
                event["is_delayed"],
                event["delay_hours"],
                message.partition,
                message.offset,
            ),
        )

        conn.commit()

        print(
            f"Stored: "
            f"{event['container_number']} | "
            f"{event['milestone']}"
        )

    except Exception as e:
        conn.rollback()
        print("ERROR:", e)