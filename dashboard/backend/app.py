from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ================= SAFE UTILS =================
def safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def safe_datetime(v):
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return datetime.now()


# ================= API =================
@app.route("/buses")
def get_buses():
    conn = get_conn()
    cur = conn.cursor()

    # ✅ CHỈ LẤY XE CÒN ONLINE (≤ 30s)
    cur.execute("""
        SELECT 
            s.bus_id,
            b.route_id,
            s.lat,
            s.lon,
            s.speed,
            s.direction,
            s.last_update
        FROM bus_current_status s
        JOIN buses b ON s.bus_id = b.bus_id
        WHERE s.last_update >= NOW() - INTERVAL '30 seconds'
        ORDER BY s.bus_id
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []

    for bus_id, route_id, lat, lon, speed, direction, last_update in rows:
        lat = safe_float(lat)
        lon = safe_float(lon)

        # 🚨 GPS rác → bỏ
        if lat is None or lon is None:
            continue

        result.append({
            "bus_id": str(bus_id),
            "route_id": int(route_id),   # ⭐ frontend dùng
            "lat": lat,
            "lon": lon,
            "speed": safe_int(speed),
            "direction": safe_int(direction),
            "updated_at": safe_datetime(last_update).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        })

    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ================= MAIN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
