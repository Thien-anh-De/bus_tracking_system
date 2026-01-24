import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_route_id_by_bus(bus_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT route_id FROM buses WHERE bus_id = %s",
        (bus_id,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row[0] if row else None

def get_stops_by_route_id(route_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.stop_id, s.stop_name, s.lat, s.lon, rs.stop_order
        FROM route_stops rs
        JOIN stops s ON rs.stop_id = s.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.stop_order
    """, (route_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
