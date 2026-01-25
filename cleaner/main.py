import os
import psycopg2
import time
from datetime import datetime, timedelta

# Lấy cấu hình từ môi trường
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "bus_tracking_system")
DB_USER = os.getenv("DB_USER", "bus_user")
DB_PASS = os.getenv("DB_PASSWORD", "Thienanh1906@")

# TEST: 1 phút | THỰC TẾ: days=3
RETENTION_DELTA = timedelta(minutes=1) 

def run_cleanup():
    try:
        with psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS) as conn:
            with conn.cursor() as cur:
                limit_ts = datetime.now() - RETENTION_DELTA
                cur.execute("DELETE FROM bus_gps_log WHERE ts < %s", (limit_ts,))
                if cur.rowcount > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧹 Đã xóa {cur.rowcount} logs cũ.")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    print(f"🚀 Cleaner started. Retention: {RETENTION_DELTA}")
    while True:
        run_cleanup()
        time.sleep(30)