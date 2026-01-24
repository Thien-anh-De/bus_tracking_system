from confluent_kafka import Consumer
import json
from math import sqrt
from streaming.db_reader import get_route_id_by_bus, get_stops_by_route_id

# ===============================
# CẤU HÌNH
# ===============================
ARRIVAL_THRESHOLD = 0.0015      # ~100m
NEAR_THRESHOLD = ARRIVAL_THRESHOLD * 2  # vùng đệm an toàn

def distance(lat1, lon1, lat2, lon2):
    return sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

print("Kafka Consumer started (FINAL VERSION)...")

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "bus-event-detector",
    # ĐỌC LẠI DATA KHI RESTART → KHÔNG MẤT EVENT
    "auto.offset.reset": "earliest",
    # Commit thủ công để ổn định
    "enable.auto.commit": False
})

consumer.subscribe(["bus_location"])

# ===============================
# TRẠNG THÁI TỪNG XE
# ===============================
bus_state = {}

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print(msg.error())
            continue

        bus = json.loads(msg.value().decode("utf-8"))
        bus_id = bus["bus_id"]
        lat = bus["lat"]
        lon = bus["lon"]

        # Lấy tuyến của xe
        route_id = get_route_id_by_bus(bus_id)
        if route_id is None:
            continue

        # Lấy danh sách trạm của tuyến
        stops = get_stops_by_route_id(route_id)
        if not stops:
            continue

        # Khởi tạo trạng thái xe
        if bus_id not in bus_state:
            bus_state[bus_id] = {
                "direction": "forward",   # forward | backward
                "last_stop_index": -1
            }

        state = bus_state[bus_id]

        # Sắp xếp trạm theo chiều di chuyển
        ordered_stops = stops if state["direction"] == "forward" else list(reversed(stops))

        # ===============================
        # CHECK XE TỚI TRẠM
        # ===============================
        for idx, stop in enumerate(ordered_stops):
            stop_id, stop_name, stop_lat, stop_lon, stop_order = stop

            # Không check lại trạm đã qua
            if idx <= state["last_stop_index"]:
                continue

            d = distance(lat, lon, stop_lat, stop_lon)

            # DEBUG KHI XE ĐI GẦN TRẠM
            if d < NEAR_THRESHOLD:
                print(f"[DEBUG] Xe {bus_id} gần {stop_name}, d={d:.6f}")

            if d < ARRIVAL_THRESHOLD:
                direction_text = "chiều đi" if state["direction"] == "forward" else "chiều về"

                print(f"[EVENT] Xe {bus_id} đến {stop_name} ({direction_text})")

                state["last_stop_index"] = idx

                # Nếu tới trạm cuối → đổi chiều
                if idx == len(ordered_stops) - 1:
                    state["direction"] = (
                        "backward" if state["direction"] == "forward" else "forward"
                    )
                    state["last_stop_index"] = -1
                    print(f"[STATE] Xe {bus_id} quay đầu")

                # Commit offset SAU khi xử lý event
                consumer.commit(msg)

                break

except KeyboardInterrupt:
    pass
finally:
    consumer.close()
