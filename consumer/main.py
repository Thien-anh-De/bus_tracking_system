from confluent_kafka import Consumer
import json
from math import sqrt
import os
import time

from streaming.db_reader import get_route_id_by_bus, get_stops_by_route_id

# ===============================
# CẤU HÌNH (DOCKER)
# ===============================
KAFKA_BROKERS = "kafka:9093"   # ❗ service name, KHÔNG localhost
KAFKA_TOPIC = "bus_location"
GROUP_ID = "bus-event-detector"

ARRIVAL_THRESHOLD = 0.0015        # ~100m
NEAR_THRESHOLD = ARRIVAL_THRESHOLD * 2  # vùng đệm an toàn


# ===============================
# UTILS
# ===============================
def distance(lat1, lon1, lat2, lon2):
    return sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


print("🚀 Kafka Consumer started (DOCKER VERSION)")

# ===============================
# INIT KAFKA CONSUMER
# ===============================
consumer = Consumer({
    "bootstrap.servers": KAFKA_BROKERS,
    "group.id": GROUP_ID,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False
})

consumer.subscribe([KAFKA_TOPIC])

# ===============================
# TRẠNG THÁI TỪNG XE
# ===============================
bus_state = {}

# ===============================
# MAIN LOOP
# ===============================
try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print("Kafka error:", msg.error())
            continue

        bus = json.loads(msg.value().decode("utf-8"))
        bus_id = bus["bus_id"]
        lat = bus["lat"]
        lon = bus["lon"]

        # ===============================
        # LẤY TUYẾN XE
        # ===============================
        route_id = get_route_id_by_bus(bus_id)
        if route_id is None:
            continue

        stops = get_stops_by_route_id(route_id)
        if not stops:
            continue

        # ===============================
        # INIT STATE
        # ===============================
        if bus_id not in bus_state:
            bus_state[bus_id] = {
                "direction": "forward",   # forward | backward
                "last_stop_index": -1
            }

        state = bus_state[bus_id]

        ordered_stops = (
            stops if state["direction"] == "forward"
            else list(reversed(stops))
        )

        # ===============================
        # CHECK XE TỚI TRẠM
        # ===============================
        for idx, stop in enumerate(ordered_stops):
            stop_id, stop_name, stop_lat, stop_lon, stop_order = stop

            if idx <= state["last_stop_index"]:
                continue

            d = distance(lat, lon, stop_lat, stop_lon)

            if d < NEAR_THRESHOLD:
                print(f"[DEBUG] Xe {bus_id} gần {stop_name}, d={d:.6f}")

            if d < ARRIVAL_THRESHOLD:
                direction_text = (
                    "chiều đi" if state["direction"] == "forward"
                    else "chiều về"
                )

                print(f"[EVENT] Xe {bus_id} đến {stop_name} ({direction_text})")

                state["last_stop_index"] = idx

                # Nếu tới trạm cuối → đổi chiều
                if idx == len(ordered_stops) - 1:
                    state["direction"] = (
                        "backward"
                        if state["direction"] == "forward"
                        else "forward"
                    )
                    state["last_stop_index"] = -1
                    print(f"[STATE] Xe {bus_id} quay đầu")

                # Commit offset SAU khi xử lý event
                consumer.commit(msg)
                break

except KeyboardInterrupt:
    print("⛔ Consumer stopped")

finally:
    consumer.close()
