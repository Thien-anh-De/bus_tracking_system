# 🚌 Bus Tracking System – Real-time Streaming with Kafka & Spark

Hệ thống mô phỏng và xử lý **dữ liệu GPS xe buýt theo thời gian thực**, sử dụng **Apache Kafka** làm message broker, **Apache Spark Structured Streaming** để xử lý luồng dữ liệu, và **PostgreSQL** để lưu trữ dữ liệu lịch sử.  
Toàn bộ hệ thống được **container hóa bằng Docker Compose**.

---

## 📌 Mục tiêu hệ thống

- Mô phỏng nhiều xe buýt di chuyển theo các tuyến cố định
- Gửi dữ liệu GPS theo thời gian thực
- Xử lý và lưu trữ dữ liệu GPS bằng kiến trúc streaming
- Xây dựng nền tảng cho các bài toán:
  - Theo dõi vị trí xe buýt realtime
  - Phân tích lịch sử di chuyển
  - Phát hiện xe đến trạm / lệch tuyến (có thể mở rộng)

---

## 🏗️ Kiến trúc tổng thể

GPS Simulator (Python)
|
v
Kafka (topic: bus_location)
|
v
Spark Structured Streaming
|
v
PostgreSQL (bus_gps_log, bus_current_status, ...)


---

## 🧩 Công nghệ sử dụng

| Thành phần | Công nghệ |
|----------|----------|
| Message Broker | Apache Kafka |
| Stream Processing | Apache Spark Structured Streaming |
| Database | PostgreSQL |
| Cache / State (mở rộng) | Redis |
| Container hóa | Docker & Docker Compose |
| Ngôn ngữ | Python |

---

## 📂 Cấu trúc thư mục
```
BUS_TRACKING_SYSTEM/
├── DBMS/
│   ├── create_db.sql          # Tạo schema, bảng
│   └── insert_value.sql       # Dữ liệu mẫu (routes, stops, buses)
│
├── docker/
│   └── spark/
│       └── Dockerfile         # Custom Spark image (cài Python deps)
│
├── streaming/
│   ├── main.py                # Spark Structured Streaming job
│   ├── spark_reader.py        # Đọc Kafka stream
│   ├── db_reader.py           # Truy vấn PostgreSQL
│   ├── redis_store.py         # Ghi trạng thái realtime vào Redis
│   ├── schemas.py             # Schema Spark
│   ├── config.py              # Cấu hình DB, Kafka
│   └── test_db.py             # Test kết nối DB
│
├── kafka_consumer.py           # Consumer xử lý logic (mở rộng)
├── GPS_Simulator.py            # Mô phỏng GPS xe buýt (Kafka producer)
│
├── spark_checkpoint/           # Checkpoint Spark Streaming
├── docker-compose.yml          # Orchestrate Kafka, Spark, Postgres, Redis
├── requirements.txt            # Python dependencies
├── .env                        # Biến môi trường (DB, Kafka)
└── README.md                   # Tài liệu dự án
```
## 🚍 Mô phỏng dữ liệu GPS

- Mỗi xe buýt có:
  - `bus_id`
  - hướng di chuyển
  - tọa độ GPS (`lat`, `lon`)
  - tốc độ
  - timestamp
- Dữ liệu được gửi **liên tục theo thời gian thực** vào Kafka topic `bus_location`

---

## 🔄 Xử lý streaming với Spark

- Spark đọc dữ liệu từ Kafka bằng **Structured Streaming**
- Xử lý theo **micro-batch**
- Parse dữ liệu JSON
- Ghi dữ liệu vào PostgreSQL
- Sử dụng **checkpoint** để đảm bảo:
  - không mất dữ liệu khi restart
  - đúng offset Kafka

---

## 🗄️ Database (PostgreSQL)

Các bảng chính:

- `bus_gps_log` – lưu lịch sử GPS
- `buses` – danh sách xe buýt
- `routes` – tuyến xe
- `stops` – trạm dừng
- `route_stops` – quan hệ tuyến – trạm
- `bus_current_status` – trạng thái hiện tại (mở rộng)

---

## ▶️ Cách chạy hệ thống

### 1️⃣ Khởi động toàn bộ hệ thống

docker compose up -d
###2️⃣ Tạo Kafka topic
docker compose exec kafka kafka-topics \
  --create \
  --topic bus_location \
  --bootstrap-server kafka:9093 \
  --replication-factor 1 \
  --partitions 3
###3️⃣ Chạy GPS Simulator
python GPS_Simulator.py
###4️⃣ Spark Streaming sẽ tự động xử lý và ghi dữ liệu
🧪 Kiểm tra dữ liệu
Kiểm tra trong PostgreSQL
SELECT COUNT(*) FROM bus_gps_log;
SELECT * FROM bus_gps_log ORDER BY ts DESC LIMIT 10;
✅ Trạng thái hiện tại
✔️ Kafka hoạt động ổn định

✔️ Spark Structured Streaming chạy realtime

✔️ Dữ liệu GPS được ghi vào PostgreSQL

✔️ Hệ thống container hóa hoàn chỉnh

##🚀 Hướng phát triển (Future Work)
Hiển thị bản đồ realtime (Leaflet / Mapbox)

Phát hiện xe đến trạm

Cảnh báo xe trễ tuyến

Dashboard giám sát (Grafana)

Machine Learning dự đoán thời gian đến trạm

📖 Ghi chú
Dự án được xây dựng nhằm mục đích học tập và nghiên cứu kiến trúc xử lý dữ liệu thời gian thực (Big Data Streaming).

👤 Tác giả
Hoàng Thiện Anh Nguyễn
