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

SLEEP_TIME = 0.5
EARTH_RADIUS = 6371000

STOP_RADIUS = 20        # m
SLOW_RADIUS = 80        # m
STOP_TIME = 12          # s

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "bus_tracking_system",
    "user": "bus_user",
    "password": "Thienanh1906@"
}

# ======================================================
# LOGGER
# ======================================================
def log(msg):
    print(f"[SIMU {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ======================================================
# KAFKA
# ======================================================
producer = Producer({
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "linger.ms": 10
})

# ======================================================
# GEO
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
    segs, total = [], 0.0
    for i in range(len(points) - 1):
        d = haversine(*points[i], *points[i + 1])
        segs.append((points[i], points[i + 1], total, total + d))
        total += d
    return segs, total


def locate(segs, dist):
    for a, b, s, e in segs:
        if s <= dist <= e:
            r = (dist - s) / (e - s) if e > s else 0
            return (
                a[0] + (b[0] - a[0]) * r,
                a[1] + (b[1] - a[1]) * r
            )
    return segs[-1][1]

# ======================================================
# LOAD DATA
# ======================================================
log("🚀 Simulator starting...")

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT bus_id, route_id FROM buses")
bus_rows = cur.fetchall()

routes = {}
buses = []

for bus_id, route_id in bus_rows:
    # route points
    cur.execute("""
        SELECT lat, lon
        FROM route_points
        WHERE route_id = %s
        ORDER BY point_order
    """, (route_id,))
    pts = cur.fetchall()

    # route stops
    cur.execute("""
        SELECT s.stop_id, s.lat, s.lon
        FROM route_stops rs
        JOIN stops s ON rs.stop_id = s.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.stop_order
    """, (route_id,))
    stops = cur.fetchall()

    if route_id not in routes:
        fwd, flen = build_segments(pts)
        bwd, blen = build_segments(list(reversed(pts)))
        routes[route_id] = {
            0: (fwd, flen, pts[0], pts[-1]),
            1: (bwd, blen, pts[-1], pts[0])
        }

    base_speed = random.randint(35, 50)

    buses.append({
        "bus_id": bus_id,
        "route_id": route_id,
        "direction": 0,
        "segments": routes[route_id][0][0],
        "route_len": routes[route_id][0][1],
        "dist": 0.0,
        "base_speed": base_speed,
        "speed": base_speed,
        "stops": stops,
        "next_stop": 0,
        "stop_until": None,
        "trip_id": 1
    })

    log(f"🚌 Loaded bus {bus_id} | base_speed={base_speed}")

cur.close()
conn.close()

log("✅ Simulator READY")
log("------------------------------------------")

# ======================================================
# MAIN LOOP
# ======================================================
while True:
    now = time.time()

    for b in buses:
        lat, lon = locate(b["segments"], b["dist"])

        # ===== STOP LOGIC =====
        speed = b["speed"]

        if b["stop_until"] and now < b["stop_until"]:
            speed = 0

        elif b["next_stop"] < len(b["stops"]):
            _, slat, slon = b["stops"][b["next_stop"]]
            d = haversine(lat, lon, slat, slon)

            if d < STOP_RADIUS:
                speed = 0
                b["stop_until"] = now + STOP_TIME
                b["next_stop"] += 1
                log(f"🛑 {b['bus_id']} dừng bến {b['next_stop']}")

            elif d < SLOW_RADIUS:
                speed = max(10, int(b["base_speed"] * 0.4))

            else:
                speed = max(
                    10,
                    min(55, b["base_speed"] + random.randint(-3, 3))
                )
        else:
            speed = max(
                10,
                min(55, b["base_speed"] + random.randint(-3, 3))
            )

        b["speed"] = speed
        b["dist"] += (speed * 1000 / 3600) * SLEEP_TIME

        # ===== END ROUTE =====
        if b["dist"] >= b["route_len"]:
            b["direction"] = 1 - b["direction"]
            seg, ln, _, _ = routes[b["route_id"]][b["direction"]]
            b.update({
                "segments": seg,
                "route_len": ln,
                "dist": 0.0,
                "trip_id": b["trip_id"] + 1,
                "next_stop": 0,
                "stop_until": None
            })
            log(f"🔁 {b['bus_id']} đổi chiều | trip {b['trip_id']}")

        payload = {
            "bus_id": b["bus_id"],
            "route_id": b["route_id"],
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "speed": int(speed),
            "direction": b["direction"],
            "trip_id": b["trip_id"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        producer.produce(TOPIC, json.dumps(payload))
        producer.poll(0)

        log(f"📤 {b['bus_id']} | {payload['lat']},{payload['lon']} | spd={speed}")

    time.sleep(SLEEP_TIME)
