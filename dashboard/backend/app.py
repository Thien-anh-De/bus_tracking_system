from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn

app = Flask(__name__)
CORS(app)

# ================= API =================

@app.route("/api/buses")
def buses():
    conn = get_conn()
    cur = conn.cursor()

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
        ORDER BY s.bus_id
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {
            "bus_id": r[0],
            "route_id": r[1],
            "lat": float(r[2]),
            "lon": float(r[3]),
            "speed": r[4],
            "direction": r[5],
            # ✅ FIX OFFLINE: ISO 8601
            "updated_at": r[6].isoformat()
        }
        for r in rows
    ])


@app.route("/api/stops")
def stops():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
          s.stop_id,
          s.stop_name,
          s.lat,
          s.lon,
          json_agg(
            json_build_object(
              'route_id', rs.route_id,
              'stop_order', rs.stop_order
            )
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
        {
            "stop_id": r[0],
            "stop_name": r[1],
            "lat": float(r[2]),
            "lon": float(r[3]),
            "routes": r[4]
        }
        for r in rows
    ])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
