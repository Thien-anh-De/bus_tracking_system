import time
import json
import random
from datetime import datetime
from math import sqrt
from confluent_kafka import Producer

# ===============================
# CẤU HÌNH KAFKA
# ===============================
producer = Producer({
    "bootstrap.servers": "localhost:9092"
})

TOPIC = "bus_location"

# ===============================
# DỮ LIỆU TỪ DATABASE (CẬP NHẬT TỌA ĐỘ CHÍNH XÁC)
# ===============================
STOPS_DATA = {
    1: (10.7416, 106.6354),  # Ben xe Mien Tay
    2: (10.7629, 106.6333),  # Cong vien Dam Sen
    3: (10.7769, 106.6675),  # San van dong Phu Tho
    4: (10.7722, 106.6694),  # Nga Sau Dan Chu
    5: (10.8126, 106.6786),  # Cong vien Gia Dinh
    6: (10.8188, 106.6520),  # San bay Tan Son Nhat
    7: (10.8357, 106.6411),  # Quang Trung
    8: (10.8443, 106.6056),  # Ben xe An Suong
    9: (10.7720, 106.6602),  # Dai hoc Bach Khoa
    10: (10.7536, 106.6610), # Benh vien Cho Ray
    11: (10.7501, 106.6572), # An Dong
    12: (10.7546, 106.6631), # Cho Lon
    13: (10.8026, 106.7146), # Ben xe Mien Dong
    14: (10.8019, 106.7106), # Nga Tu Hang Xanh
}

ROUTES = {
    1: [1, 2, 3, 4, 5, 6, 7, 8],      
    2: [1, 2, 3, 4, 9, 10, 11, 12],   
    3: [13, 14, 5, 6, 7, 8],          
    4: [5, 6, 4, 9, 10, 11, 12]       
}

# ===============================
# KHỞI TẠO 5 XE (Khớp với bảng buses)
# ===============================
buses = [
    {"bus_id": "01", "route_id": 1, "stops": ROUTES[1], "current_idx": 0, "dir": 1},
    {"bus_id": "02", "route_id": 1, "stops": ROUTES[1], "current_idx": 4, "dir": 1},
    {"bus_id": "03", "route_id": 2, "stops": ROUTES[2], "current_idx": 0, "dir": 1},
    {"bus_id": "04", "route_id": 3, "stops": ROUTES[3], "current_idx": 0, "dir": 1},
    {"bus_id": "05", "route_id": 4, "stops": ROUTES[4], "current_idx": 0, "dir": 1},
]

for b in buses:
    start_pos = STOPS_DATA[b["stops"][b["current_idx"]]]
    b["lat"], b["lon"] = start_pos

STEP = 0.0006  

print("🚍 GPS Simulator is running for 5 buses...")
print("Press Ctrl+C to stop.\n")

# ===============================
# VÒNG LẶP GIẢ LẬP CHÍNH
# ===============================
try:
    while True:
        for b in buses:
            # 1. Xác định trạm mục tiêu
            target_stop_id = b["stops"][b["current_idx"] + b["dir"]]
            tlat, tlon = STOPS_DATA[target_stop_id]

            # 2. Tính toán di chuyển
            dlat = tlat - b["lat"]
            dlon = tlon - b["lon"]
            dist = sqrt(dlat**2 + dlon**2)

            # 3. Kiểm tra trạm dừng & Đảo chiều
            if dist < 0.0008:
                b["current_idx"] += b["dir"]
                if b["current_idx"] + b["dir"] >= len(b["stops"]) or b["current_idx"] + b["dir"] < 0:
                    b["dir"] *= -1
            else:
                b["lat"] += STEP * dlat / dist
                b["lon"] += STEP * dlon / dist

            # 4. Tạo Payload
            payload = {
                "bus_id": b["bus_id"],
                "lat": round(b["lat"], 6),
                "lon": round(b["lon"], 6),
                "speed": random.randint(30, 50),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 5. Gửi vào Kafka
            producer.produce(TOPIC, value=json.dumps(payload))
            
            # 6. IN LOG (Kết hợp thông số và trạng thái trạm)
            direction_str = ">>" if b["dir"] == 1 else "<<"
            print(f"[{payload['timestamp']}] Bus {b['bus_id']} {direction_str} To Stop {target_stop_id} | GPS: ({payload['lat']}, {payload['lon']})")

        producer.poll(0)
        print("-" * 85) # Ngăn cách mỗi giây dữ liệu
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Simulator stopped.")