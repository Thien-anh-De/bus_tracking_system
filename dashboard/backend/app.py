import os
import json
import time
import math
import redis
from flask import Flask, jsonify, Response
from flask_cors import CORS
from db import get_conn

app = Flask(__name__)
CORS(app)

# =====================
# REDIS CONNECTION
# =====================
def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )

# =====================
# GEO HELPERS (Backend ETA)
# =====================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_along_route(route_points, lat, lon):
    """Tính khoảng cách dọc theo polyline tới vị trí gần nhất với (lat, lon)."""
    acc = 0.0
    best = 0.0
    min_err = float("inf")
    for i in range(len(route_points) - 1):
        a_lat, a_lon = route_points[i]
        b_lat, b_lon = route_points[i + 1]
        ab = haversine_km(a_lat, a_lon, b_lat, b_lon)
        ax = haversine_km(a_lat, a_lon, lat, lon)
        xb = haversine_km(lat, lon, b_lat, b_lon)
        err = abs(ab - (ax + xb))
        if err < min_err:
            min_err = err
            best = acc + ax
        acc += ab
    return best

# =====================
# READ BUSES FROM REDIS (với fallback về PostgreSQL)
# =====================
def read_buses_from_redis():
    """
    Đọc toàn bộ vị trí xe buýt từ Redis.
    Key pattern: bus:{bus_id}:location  (lưu bởi Spark streaming)
    Fallback về PostgreSQL nếu Redis không có dữ liệu.
    """
    try:
        r = get_redis()
        keys = r.keys("bus:*:location")
        if not keys:
            raise ValueError("Redis empty, fallback to PostgreSQL")

        buses = []
        for key in keys:
            bus_id = key.split(":")[1]
            loc_raw = r.get(key)
            ts = r.get(f"bus:{bus_id}:last_update") or ""
            if not loc_raw:
                continue
            loc = json.loads(loc_raw)

            # Lấy route_id từ PostgreSQL (cache trong memory đơn giản)
            route_id = _bus_route_cache().get(bus_id)

            buses.append({
                "bus_id": bus_id,
                "route_id": route_id,
                "lat": loc["lat"],
                "lon": loc["lon"],
                "speed": loc["speed"],
                "direction": loc.get("direction", 0),
                "updated_at": ts,
                "source": "redis"
            })

        buses.sort(key=lambda x: x["bus_id"])
        return buses

    except Exception as e:
        # Fallback về PostgreSQL
        print(f"[WARN] Redis read failed ({e}), falling back to PostgreSQL")
        return _read_buses_from_postgres()


_route_cache = {}

def _bus_route_cache():
    """Cache bus_id -> route_id từ PostgreSQL để tránh query liên tục."""
    global _route_cache
    if not _route_cache:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT bus_id, route_id FROM buses")
            for bus_id, route_id in cur.fetchall():
                _route_cache[bus_id] = route_id
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] route cache load failed: {e}")
    return _route_cache


def _read_buses_from_postgres():
    """Fallback: đọc trực tiếp từ PostgreSQL."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.bus_id, b.route_id, s.lat, s.lon, s.speed, s.direction, s.last_update
            FROM bus_current_status s
            JOIN buses b ON s.bus_id = b.bus_id
            ORDER BY s.bus_id
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "bus_id": r[0],
                "route_id": r[1],
                "lat": float(r[2]),
                "lon": float(r[3]),
                "speed": r[4],
                "direction": r[5],
                "updated_at": r[6].isoformat() if r[6] else "",
                "source": "postgres"
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[ERROR] Postgres fallback failed: {e}")
        return []

# =====================
# API: GET /api/buses  (giữ lại để tương thích, giờ đọc từ Redis)
# =====================
@app.route("/api/buses")
def buses():
    return jsonify(read_buses_from_redis())


# =====================
# API: GET /api/stream/buses  (SSE - Server-Sent Events)
# =====================
@app.route("/api/stream/buses")
def stream_buses():
    """
    Server-Sent Events endpoint.
    Frontend chỉ cần mở 1 kết nối, server tự push data mỗi 1.5 giây.
    Thay thế hoàn toàn cho setInterval + fetch polling.
    """
    def generate():
        while True:
            try:
                data = read_buses_from_redis()
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(1.5)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Quan trọng: tắt buffer của nginx
            "Connection": "keep-alive"
        }
    )


# =====================
# API: GET /api/stops  (giữ nguyên, đọc từ PostgreSQL)
# =====================
@app.route("/api/stops")
def stops():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
          s.stop_id, s.stop_name, s.lat, s.lon,
          json_agg(
            json_build_object('route_id', rs.route_id, 'stop_order', rs.stop_order)
            ORDER BY rs.stop_order
          )
        FROM stops s
        JOIN route_stops rs ON s.stop_id = rs.stop_id
        GROUP BY s.stop_id
        ORDER BY s.stop_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"stop_id": r[0], "stop_name": r[1], "lat": float(r[2]), "lon": float(r[3]), "routes": r[4]}
        for r in rows
    ])


# =====================
# API: GET /api/stops/eta/<stop_id>  (ETA tính tại Backend)
# =====================

# Cache route_points để không phải query DB liên tục
_route_points_cache = {}
_stop_routes_cache  = {}

def _load_route_points(route_id):
    global _route_points_cache
    if route_id not in _route_points_cache:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT lat, lon FROM route_points
            WHERE route_id = %s ORDER BY point_order
        """, (route_id,))
        _route_points_cache[route_id] = cur.fetchall()
        cur.close()
        conn.close()
    return _route_points_cache[route_id]


def _load_stop_routes(stop_id):
    global _stop_routes_cache
    if stop_id not in _stop_routes_cache:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT route_id FROM route_stops WHERE stop_id = %s
        """, (stop_id,))
        _stop_routes_cache[stop_id] = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    return _stop_routes_cache[stop_id]


@app.route("/api/stops/eta/<int:stop_id>")
def get_eta(stop_id):
    """
    Tính ETA cho tất cả xe buýt sắp đến bến stop_id.
    Toàn bộ thuật toán Distance-Along-Route chạy tại server.
    """
    try:
        # Lấy thông tin bến
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT stop_name, lat, lon FROM stops WHERE stop_id = %s", (stop_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Stop not found"}), 404

        stop_name, stop_lat, stop_lon = row[0], float(row[1]), float(row[2])

        # Các tuyến đi qua bến này
        valid_routes = _load_stop_routes(stop_id)

        # Lấy vị trí tất cả xe từ Redis
        all_buses = read_buses_from_redis()

        result = []
        for bus in all_buses:
            route_id = bus.get("route_id")
            if route_id not in valid_routes:
                continue
            if not bus.get("speed") or bus["speed"] <= 0:
                continue

            route_pts = _load_route_points(route_id)
            if not route_pts:
                continue

            bus_d  = distance_along_route(route_pts, bus["lat"], bus["lon"])
            stop_d = distance_along_route(route_pts, stop_lat, stop_lon)

            if bus_d >= stop_d:
                continue  # Xe đã đi qua bến

            remaining_km = stop_d - bus_d
            speed_kmh = bus["speed"]
            eta_min = (remaining_km / speed_kmh) * 60

            if eta_min < 30:
                result.append({
                    "bus_id": bus["bus_id"],
                    "route_id": route_id,
                    "eta_min": round(eta_min, 1),
                    "speed": speed_kmh,
                    "distance_km": round(remaining_km, 2)
                })

        result.sort(key=lambda x: x["eta_min"])

        return jsonify({
            "stop_id": stop_id,
            "stop_name": stop_name,
            "buses": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================
# HEALTH CHECK
# =====================
@app.route("/health")
def health():
    redis_ok = False
    try:
        r = get_redis()
        r.ping()
        redis_ok = True
    except Exception:
        pass
    return jsonify({"status": "ok", "redis": redis_ok})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
