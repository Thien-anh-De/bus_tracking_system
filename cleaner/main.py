import os
import psycopg2
import time
from datetime import datetime, timedelta

# ===============================
# CẤU HÌNH DATABASE
# ===============================
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "bus_tracking_system")
DB_USER = os.getenv("DB_USER", "bus_user")
DB_PASS = os.getenv("DB_PASSWORD", "Thienanh1906@")

# TEST: 1 phút | THỰC TẾ: days=3
RETENTION_DELTA = timedelta(minutes=10)

def run_cleanup():
    now = datetime.now()
    print(f"🔍 Checking for old logs at {now}", flush=True)

    try:
        with psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        ) as conn:
            with conn.cursor() as cur:
                limit_ts = now - RETENTION_DELTA
                cur.execute(
                    "DELETE FROM bus_gps_log WHERE ts < %s",
                    (limit_ts,)
                )

                if cur.rowcount > 0:
                    print(
                        f"[{datetime.now():%H:%M:%S}] 🧹 Deleted {cur.rowcount} old logs",
                        flush=True
                    )
                else:
                    print(
                        f"[{datetime.now():%H:%M:%S}] ℹ️ No old logs to delete",
                        flush=True
                    )

    except Exception as e:
        print(f"❌ Cleanup error: {e}", flush=True)


if __name__ == "__main__":
    print(f"🚀 Cleaner started. Retention: {RETENTION_DELTA}", flush=True)

    while True:
        run_cleanup()
        time.sleep(30)
