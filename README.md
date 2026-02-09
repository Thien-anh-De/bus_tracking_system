# 🚌 Bus Tracking System  
### Nền tảng theo dõi xe buýt realtime & dự đoán ETA

**Bus Tracking System** là một hệ thống **full-stack theo thời gian thực**, mô phỏng chuyển động xe buýt, xử lý dữ liệu GPS dạng streaming và trực quan hóa **xe buýt – tuyến đường – bến xe – ETA** trên bản đồ tương tác.

> Dự án thể hiện năng lực thực hành về **Hệ phân tán (Distributed Systems)**, **Dữ liệu thời gian thực (Streaming Data)**, **Backend API**, và **Realtime Visualization**, phù hợp sử dụng cho **portfolio cá nhân và CV**.

---

## 📌 Bài toán đặt ra

Hệ thống giao thông công cộng cần:
- Theo dõi phương tiện theo thời gian thực
- Ước lượng chính xác thời gian xe đến bến (ETA)
- Trực quan hóa dữ liệu dễ hiểu cho người dùng và nhà vận hành

Tuy nhiên, nhiều hệ thống demo thường gặp vấn đề:
- Trộn xe của các tuyến khác nhau khi tính ETA
- Tính ETA bằng khoảng cách thẳng → sai lệch lớn
- Dữ liệu realtime không nhất quán

👉 Dự án này giải quyết các hạn chế trên bằng cách xây dựng **hệ thống theo dõi xe buýt realtime có nhận thức tuyến (route-aware)** từ đầu.

---

## 🎯 Mục tiêu dự án

- Mô phỏng chuyển động xe buýt trên các tuyến cố định
- Theo dõi nhiều xe buýt theo thời gian thực
- Tính **ETA chính xác cho từng bến, từng tuyến**
- Hiển thị dữ liệu realtime trên bản đồ tương tác
- Thiết kế kiến trúc rõ ràng, dễ mở rộng

---

## 🏗️ Kiến trúc hệ thống
```
┌────────────────────┐
│ Bus Simulator      │
│ (Python)           │
│ - Theo tuyến       │
│ - Tốc độ ngẫu nhiên│
└────────┬───────────┘
│ Sự kiện GPS
         ▼
┌────────────────────┐
│ Apache Kafka       │
│ Event Broker       │
└────────┬───────────┘
         ▼
┌────────────────────────────┐
│ PostgreSQL                 │
│ - bus_current_status       │
│ - bus_gps_log              │
│ - routes / stops           │
└────────┬───────────────────┘
         ▼
┌────────────────────────────┐
│ Flask Backend API          │
│ - /api/buses               │
│ - /api/stops               │
│ - /api/bus/:id/gps-log     │
└────────┬───────────────────┘
         ▼
┌────────────────────────────┐
│ Frontend Dashboard         │
│ - LeafletJS + OSM          │
│ - Realtime rendering       │
└────────────────────────────┘
```
## ⚙️ Công nghệ sử dụng

### Backend & Dữ liệu
- **Python**
- **Flask** (REST API)
- **Apache Kafka**
- **PostgreSQL**
- **psycopg2**

### Frontend
- **HTML / CSS / JavaScript**
- **Leaflet.js**
- **OpenStreetMap**

### Hạ tầng
- **Docker**
- **Docker Compose**

---

## 📁 Cấu trúc thư mục
```
bus_tracking_system/
├── simulator/
│ └── bus_simulator.py
│
├── backend/
│ ├── app.py
│ ├── db.py
│ └── requirements.txt
│
├── dashboard/
│ ├── index.html
│ ├── map.js
│ └── routes.json
│
├── docker-compose.yml
└── README.md
```


## 🚍 Bus Simulator

### Chức năng chính
- Mỗi xe buýt có:
  - `bus_id`
  - `route_id`
  - `direction`
  - `speed` (ngẫu nhiên)
- Di chuyển **dọc theo hình học tuyến thực tế**
- Tự động đổi chiều khi đến cuối tuyến
- Phát dữ liệu GPS liên tục qua Kafka

### Ý nghĩa
✔ Không teleport ngẫu nhiên  
✔ Tốc độ sát thực tế  
✔ Chuyển động có hướng rõ ràng  

---

## 🗄️ Thiết kế cơ sở dữ liệu

### Các bảng chính
- `buses`
- `routes`
- `route_points`
- `stops`
- `route_stops`
- `bus_current_status`
- `bus_gps_log`

### Điểm nổi bật
- Chuẩn hóa quan hệ tuyến – bến
- Lưu thứ tự bến theo từng tuyến
- Tách dữ liệu realtime và lịch sử GPS

---

## 🌐 Backend API (Flask)

### `GET /api/buses`
Trả về **trạng thái realtime của toàn bộ xe buýt**
```json
{
  "bus_id": "01",
  "route_id": 1,
  "lat": 20.9601,
  "lon": 105.7602,
  "speed": 36,
  "direction": 0,
  "updated_at": "2026-02-09 12:30:21"
}
GET /api/stops
Danh sách bến xe kèm các tuyến đi qua

json
Copy code
{
  "stop_id": 5,
  "stop_name": "Ga tàu điện La Khê",
  "lat": 20.975,
  "lon": 105.765,
  "routes": [
    { "route_id": 1, "stop_order": 4 },
    { "route_id": 2, "stop_order": 6 }
  ]
}
```
## 🗺️ Dashboard Frontend
Tính năng bản đồ
- Hiển thị toàn bộ tuyến xe
- Hiển thị bến xe
- Hiển thị xe buýt đang di chuyển (icon màu)
- Cập nhật realtime mỗi 2 giây

Tương tác bến xe
- Click bến → hiển thị ETA
- Chỉ hiển thị các xe:
  - Thuộc tuyến đi qua bến
  - Chưa đi qua bến
  - 
### ⏱️Tính ETA (Điểm then chốt)

Vấn đề
Khoảng cách thẳng không phản ánh đúng thời gian di chuyển trên tuyến cong.

Giải pháp
Tính khoảng cách dọc theo tuyến (distance along route):

Các bước:
- Chiếu vị trí xe lên polyline tuyến
- Chiếu vị trí bến lên cùng tuyến
- Loại xe đã đi qua bến

Tính:
```
ETA = (khoảng cách còn lại / vận tốc)
Kết quả
✔ Không trộn tuyến
✔ Không tính xe đi ngược
✔ ETA chính xác, ổn định
```
### 📊 Bảng log realtime
Hiển thị:
- ID xe
- Vận tốc hiện tại
- Bến sắp tới (xác định theo tuyến)

## 🧠 Thách thức & cách giải quyết
- ETA hiển thị xe sai tuyến
→ Lọc chặt theo route_id & route_stops

- Popup bến chỉ xem được một lần
→ Quản lý vòng đời popup & state

- UI realtime không nhất quán
→ Dùng state tập trung (busState)

## 🚀 Hướng phát triển tiếp
- WebSocket thay cho polling
- Mô phỏng dừng xe & tăng/giảm tốc
- Phân tích trễ chuyến
- Mô phỏng lượng hành khách
- Dashboard quản trị ITS

## 👤 Tác giả
Nguyễn Hoàng Thiện Anh
Realtime Bus Tracking System
Dự án Full-stack / Data / Streaming
