import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from kafka import KafkaProducer


TOPIC_NAME = "container-tracking-events"
BOOTSTRAP_SERVERS = "localhost:9092"

CONTAINER_PREFIXES = [
    ("MSCU", "MSC"),
    ("MAEU", "Maersk"),
    ("HLCU", "Hapag-Lloyd"),
    ("CMAU", "CMA CGM"),
    ("OOLU", "OOCL"),
]

ROUTES = [
    {
        "origin": "CNSHA",
        "port_of_discharge": "USLAX",
        "destination": "USPHX",
    },
    {
        "origin": "CNNGB",
        "port_of_discharge": "USLGB",
        "destination": "USDFW",
    },
    {
        "origin": "VNSGN",
        "port_of_discharge": "USSEA",
        "destination": "USCHI",
    },
    {
        "origin": "INMUN",
        "port_of_discharge": "USNYC",
        "destination": "USCLT",
    },
    {
        "origin": "SGSIN",
        "port_of_discharge": "USSAV",
        "destination": "USATL",
    },
]

MILESTONES = [
    ("BOOKED", 0, "origin"),
    ("GATE_IN", 2, "origin"),
    ("LOADED_ON_VESSEL", 4, "origin"),
    ("VESSEL_DEPARTED", 5, "origin"),
    ("VESSEL_ARRIVED", 25, "port_of_discharge"),
    ("DISCHARGED", 26, "port_of_discharge"),
    ("AVAILABLE_FOR_PICKUP", 27, "port_of_discharge"),
    ("GATE_OUT", 28, "port_of_discharge"),
    ("DELIVERED", 31, "destination"),
]


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        key_serializer=lambda key: key.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        retries=3,
    )


def generate_container_number(prefix: str) -> str:
    return f"{prefix}{random.randint(1000000, 9999999)}"


def create_containers(count: int) -> List[Dict]:
    containers = []

    for _ in range(count):
        prefix, carrier = random.choice(CONTAINER_PREFIXES)
        route = random.choice(ROUTES)

        containers.append(
            {
                "container_number": generate_container_number(prefix),
                "carrier": carrier,
                "origin": route["origin"],
                "port_of_discharge": route["port_of_discharge"],
                "destination": route["destination"],
                "is_delayed": random.random() < 0.15,
                "delay_hours": random.choice([12, 24, 36, 48, 72]),
            }
        )

    return containers


def create_event(
    container: Dict,
    milestone: str,
    day_offset: int,
    location_field: str,
    base_timestamp: datetime,
) -> Dict:
    delay_hours = container["delay_hours"] if container["is_delayed"] else 0

    planned_timestamp = base_timestamp + timedelta(days=day_offset)
    actual_timestamp = planned_timestamp + timedelta(hours=delay_hours)

    return {
        "event_id": (
            f"{container['container_number']}-"
            f"{milestone}-"
            f"{int(actual_timestamp.timestamp())}"
        ),
        "container_number": container["container_number"],
        "carrier": container["carrier"],
        "milestone": milestone,
        "location": container[location_field],
        "origin": container["origin"],
        "port_of_discharge": container["port_of_discharge"],
        "destination": container["destination"],
        "planned_timestamp": planned_timestamp.isoformat(),
        "event_timestamp": actual_timestamp.isoformat(),
        "is_delayed": container["is_delayed"],
        "delay_hours": delay_hours,
    }


def main() -> None:
    producer = create_producer()
    containers = create_containers(count=20)

    base_timestamp = datetime.now(timezone.utc)
    total_events = 0

    print(f"Starting simulation for {len(containers)} containers...\n")

    try:
        for milestone, day_offset, location_field in MILESTONES:
            for container in containers:
                event = create_event(
                    container=container,
                    milestone=milestone,
                    day_offset=day_offset,
                    location_field=location_field,
                    base_timestamp=base_timestamp,
                )

                future = producer.send(
                    TOPIC_NAME,
                    key=container["container_number"],
                    value=event,
                )

                future.get(timeout=10)
                total_events += 1

            producer.flush()

            print(
                f"Published {milestone} events for "
                f"{len(containers)} containers"
            )

            time.sleep(1)

    except Exception as exc:
        print(f"Producer failed: {exc}")
        raise

    finally:
        producer.flush()
        producer.close()

    delayed_count = sum(
        1 for container in containers if container["is_delayed"]
    )

    print("\nSimulation complete")
    print(f"Containers: {len(containers)}")
    print(f"Delayed containers: {delayed_count}")
    print(f"Total events published: {total_events}")


if __name__ == "__main__":
    main()