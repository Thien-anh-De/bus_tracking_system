from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn
from datetime import datetime

app = Flask(__name__)
CORS(app)


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


@app.route("/buses")
def get_buses():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT bus_id, lat, lon, speed, direction, last_update
        FROM bus_current_status
        ORDER BY bus_id
    """)

    rows = cur.fetchall()
    conn.close()

    result = []

    for r in rows:
        bus_id, lat, lon, speed, direction, last_update = r

        lat = safe_float(lat)
        lon = safe_float(lon)
        if lat is None or lon is None:
            continue

        result.append({
            "bus_id": str(bus_id),
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
