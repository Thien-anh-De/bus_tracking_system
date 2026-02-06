import time
import json
import math
import random
from datetime import datetime

import psycopg2
from confluent_kafka import Producer

# ======================================================
# CONFIG
# ======================================================
KAFKA_BOOTSTRAP = "kafka:9093"
TOPIC = "bus_location"

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "bus_tracking_system",
    "user": "bus_user",
    "password": "Thienanh1906@"
}

SLEEP_TIME = 0.5          # giây giữa mỗi lần gửi GPS
TURNAROUND_SLEEP = 5     # dừng ở cuối tuyến
EARTH_RADIUS = 6371000
STOP_GPS_REPEAT = 3      # số bản tin GPS khi đứng bến

# ======================================================
# KAFKA
# ======================================================
producer = Producer({
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "linger.ms": 10
})

# ======================================================
# GEO HELPERS
# ======================================================
def haversine(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) *
        math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_segments(points):
    segments = []
    total = 0.0

    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i + 1]
        length = haversine(p1[0], p1[1], p2[0], p2[1])

        segments.append({
            "from": p1,
            "to": p2,
            "length": length,
            "start": total,
            "end": total + length
        })
        total += length

    return segments, total


def locate_on_segments(segments, dist):
    for s in segments:
        if s["start"] <= dist <= s["end"]:
            ratio = (dist - s["start"]) / s["length"] if s["length"] > 0 else 0
            lat = s["from"][0] + (s["to"][0] - s["from"][0]) * ratio
            lon = s["from"][1] + (s["to"][1] - s["from"][1]) * ratio
            return lat, lon

    return segments[-1]["to"]

# ======================================================
# LOAD DATA
# ======================================================
print("🚀 Simulator starting...", flush=True)

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT bus_id, route_id FROM buses")
bus_rows = cur.fetchall()

if not bus_rows:
    raise RuntimeError("❌ Bảng buses rỗng")

route_cache = {}
buses = []

for bus_id, route_id in bus_rows:
    cur.execute("""
        SELECT lat, lon
        FROM route_points
        WHERE route_id = %s
        ORDER BY point_order
    """, (route_id,))
    points = cur.fetchall()

    if len(points) < 2:
        raise RuntimeError(f"❌ Route {route_id} thiếu route_points")

    if route_id not in route_cache:
        seg_fwd, len_fwd = build_segments(points)
        seg_bwd, len_bwd = build_segments(list(reversed(points)))

        route_cache[route_id] = {
            "forward": (seg_fwd, len_fwd, points[0], points[-1]),
            "backward": (seg_bwd, len_bwd, points[-1], points[0])
        }

    buses.append({
        "bus_id": bus_id,
        "route_id": route_id,
        "direction": "forward",
        "segments": route_cache[route_id]["forward"][0],
        "route_len": route_cache[route_id]["forward"][1],
        "start_point": route_cache[route_id]["forward"][2],
        "end_point": route_cache[route_id]["forward"][3],
        "distance": 0.0,
        "speed": random.randint(35, 50),
        "trip_id": 1,
        "state": "AT_START"   # AT_START → RUNNING → AT_END
    })

cur.close()
conn.close()

print("✅ Simulator READY", flush=True)
print("------------------------------------------------", flush=True)

# ======================================================
# MAIN LOOP
# ======================================================
while True:
    for b in buses:

        # ===== ĐỨNG Ở BẾN ĐẦU =====
        if b["state"] == "AT_START":
            lat, lon = b["start_point"]

            for _ in range(STOP_GPS_REPEAT):
                payload = {
                    "bus_id": b["bus_id"],
                    "route_id": b["route_id"],
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "speed": 0,
                    "direction": b["direction"],
                    "trip_id": b["trip_id"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                producer.produce(TOPIC, json.dumps(payload))
                print(f"🅿️ BUS {b['bus_id']} đứng bến", flush=True)
                time.sleep(SLEEP_TIME)

            b["state"] = "RUNNING"
            continue

        # ===== ĐANG CHẠY =====
        if b["state"] == "RUNNING":
            speed_mps = b["speed"] * 1000 / 3600
            b["distance"] += speed_mps * SLEEP_TIME

            if b["distance"] >= b["route_len"]:
                b["state"] = "AT_END"
                continue

            lat, lon = locate_on_segments(b["segments"], b["distance"])

            payload = {
                "bus_id": b["bus_id"],
                "route_id": b["route_id"],
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "speed": b["speed"],
                "direction": b["direction"],
                "trip_id": b["trip_id"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            producer.produce(TOPIC, json.dumps(payload))
            print(
                f"📍 BUS {b['bus_id']} | {payload['lat']},{payload['lon']}",
                flush=True
            )
            continue

        # ===== ĐỨNG Ở BẾN CUỐI =====
        if b["state"] == "AT_END":
            lat, lon = b["end_point"]

            for _ in range(STOP_GPS_REPEAT):
                ppayload = {
                    "bus_id": b["bus_id"],
                    "route_id": b["route_id"],
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "speed": b["speed"],
                    "direction": 0 if b["direction"] == "forward" else 1,  # ⭐ FIX
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                producer.produce(TOPIC, json.dumps(payload))
                print(f"🛑 BUS {b['bus_id']} cuối tuyến", flush=True)
                time.sleep(SLEEP_TIME)

            # đảo chiều
            b["direction"] = "backward" if b["direction"] == "forward" else "forward"
            seg, length, start, end = route_cache[b["route_id"]][b["direction"]]
            b["segments"] = seg
            b["route_len"] = length
            b["start_point"] = start
            b["end_point"] = end
            b["distance"] = 0.0
            b["trip_id"] += 1
            b["state"] = "AT_START"

    producer.poll(0)
    time.sleep(SLEEP_TIME)
