# 🚌 Bus Tracking System - Realtime Streaming Pipeline

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-Event_Broker-black.svg)](https://kafka.apache.org/)
[![Spark](https://img.shields.io/badge/Apache_Spark-Stream_Processing-orange.svg)](https://spark.apache.org/)
[![Redis](https://img.shields.io/badge/Redis-In--Memory_State-red.svg)](https://redis.io/)
[![Flask](https://img.shields.io/badge/Flask-SSE_Backend-green.svg)](https://flask.palletsprojects.com/)

**Bus Tracking System** là một hệ thống phần mềm full-stack mô phỏng, xử lý luồng dữ liệu lớn (streaming data) và trực quan hóa vị trí xe buýt theo thời gian thực. Dự án được thiết kế theo **Kiến trúc hướng sự kiện (Event-driven Architecture)** và **Mô hình Lambda/Kappa**, với khả năng chịu tải cao, tính toán ETA (Estimated Time of Arrival) chính xác dựa trên hình học không gian, và luồng dữ liệu trơn tru từ hạ tầng Backend đến giao diện Frontend thông qua Server-Sent Events (SSE).

> **Lưu ý:** Dự án này được thiết kế theo tiêu chuẩn công nghiệp (Production-ready design patterns), thể hiện năng lực làm chủ các hệ thống phân tán, xử lý dữ liệu luồng (Streaming Data Pipeline) và kiến trúc ứng dụng Web hiệu năng cao. Phù hợp làm đồ án tốt nghiệp, bài tập lớn hoặc danh mục hồ sơ năng lực (Portfolio/CV).

---

## 🎯 Bài Toán & Giải Pháp Cốt Lõi

Hệ thống giao thông công cộng thông minh (ITS - Intelligent Transport Systems) luôn đối mặt với các thách thức về **độ trễ dữ liệu**, **tính chính xác của thời gian dự kiến (ETA)**, và **nút thắt cổ chai hiệu năng (bottleneck)** khi số lượng người dùng truy cập bản đồ đồng thời tăng cao.

Dự án này giải quyết triệt để các vấn đề trên bằng những thiết kế sau:
1. **Kiến trúc luồng dữ liệu siêu trễ thấp (Ultra-low Latency Pipeline):** Thay vì Frontend liên tục gọi (Polling) vào Database quan hệ, hệ thống sử dụng **Apache Spark** để ghi trạng thái thời gian thực trực tiếp vào RAM qua **Redis**, sau đó **Flask Backend** sử dụng giao thức **SSE (Server-Sent Events)** đẩy (push) dữ liệu lên Frontend.
2. **Thuật toán ETA nhận thức tuyến (Route-aware ETA):** Không sử dụng khoảng cách đường chim bay, hệ thống chiếu tọa độ GPS (Projection) lên ma trận polyline của tuyến đường (Distance-Along-Route) để tính toán chuẩn xác khoảng cách và thời gian di chuyển.
3. **Chuyển động mượt mà (60fps Smooth Animation):** Giải quyết bài toán giật lag tọa độ đặc trưng của các hệ thống GPS bằng thuật toán nội suy hình học (Linear Interpolation) tích hợp Easing function ngay trên giao diện bản đồ.

---

## 🏗️ Kiến Trúc Hệ Thống (System Architecture)

```text
┌────────────────────┐      ┌────────────────────┐      ┌───────────────────────────┐
│ Bus Simulator      │      │ Apache Kafka       │      │ Apache Spark (Streaming)  │
│ (Python)           ├─────►│ (Event Broker)     ├─────►│ - Windowing / Aggregation │
│ - Haversine Engine │      │ Topic: bus_location│      │ - Data Normalization      │
└────────────────────┘      └────────────────────┘      └──────┬─────────┬──────────┘
                                                               │         │
                                      ┌────────────────────────▼─┐     ┌─▼────────────────────────┐
                                      │ PostgreSQL (Cold Store)  │     │ Redis (Hot State)        │
                                      │ - bus_gps_log (History)  │     │ - bus:{id}:location      │
                                      │ - route_points / stops   │     │ - bus:{id}:last_update   │
                                      └─────────────┬────────────┘     └─┬────────────────────────┘
                                                    │                    │
┌───────────────────────────┐                 ┌─────▼────────────────────▼──┐
│ Web GIS Dashboard         │ ◄───(SSE)───────┤ Flask Backend API           │
│ - Leaflet.js / OSM        │                 │ - /api/stream/buses         │
│ - 60fps Marker Animation  │                 │ - /api/stops/eta/:id        │
└───────────────────────────┘ ◄───(Fetch)─────┤ (Spatial Math Engine)       │
                                              └─────────────────────────────┘
```

---

## ⚙️ Công Nghệ & Stack Trọng Tâm

### 1. Data Ingestion & Streaming Pipeline
- **Python Simulator:** Trình giả lập luồng GPS tạo ra hàng ngàn sự kiện với tốc độ ngẫu nhiên, tuân thủ hình học tuyến thực tế bằng công thức *Haversine*.
- **Apache Kafka (Zookeeper):** Đóng vai trò làm bộ đệm sự kiện trung tâm (Message Broker) chịu tải cao.
- **Apache Spark (Structured Streaming):** Đọc dữ liệu từ Kafka micro-batches, chuẩn hóa và tách luồng ghi song song (Forking).

### 2. Storage & Caching
- **Redis (In-memory Store):** Hoạt động như một *Write-through Cache* hoặc trạng thái Real-time. Xóa bỏ hoàn toàn áp lực truy vấn I/O lên Database quan hệ.
- **PostgreSQL:** Lưu trữ dữ liệu danh mục (Tuyến, Điểm dừng, Lộ trình) và Log lịch sử chạy xe (`bus_gps_log`) phục vụ truy vấn hoặc Data Analytics/Machine Learning sau này.

### 3. API & Presentation Layer
- **Flask (Python API):** Backend cung cấp các REST API lấy thông tin định tuyến và tính toán ETA không gian mạng. Tích hợp endpoint kết nối liên tục (Long-lived connection).
- **Server-Sent Events (SSE):** Tối ưu hóa Web socket cho luồng dữ liệu 1 chiều (One-way push) từ Server xuống Client.
- **Leaflet.js + OpenStreetMap:** Hệ thống Web GIS render bản đồ hiển thị tương tác mượt mà.
- **Nginx:** Tối ưu hóa Proxy, tắt tính năng buffering để luồng SSE được truyền đi tức thời (Zero-delay).

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

Toàn bộ hệ thống được đóng gói tự động qua Docker. Chỉ cần máy bạn đã cài đặt **Docker** và **Docker Compose**.

### Bước 1: Khởi động toàn bộ hạ tầng
```bash
docker-compose up --build -d
```
Lệnh này sẽ tự động tải các Image, cấu hình network, seed database (tạo bảng, chèn routes), khởi động Kafka, Spark job, Backend và Frontend. Quá trình có thể mất khoảng 2-5 phút trong lần chạy đầu tiên.

### Bước 2: Truy cập hệ thống
- **Web Dashboard:** `http://localhost:8080`
- **Backend API (Health check):** `http://localhost:5050/health`
- Lắng nghe luồng dữ liệu thật (Raw SSE Stream): `http://localhost:5050/api/stream/buses`

### Bước 3: Dọn dẹp
```bash
docker-compose down -v
```

---

## 🧠 Điểm Nổi Bật Về Kỹ Thuật (Technical Highlights)

### 1. Thuật toán ETA (Estimated Time of Arrival)
Thay vì sử dụng khoảng cách tuyến tính `$D = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$` (sai số cực lớn với đường cong vòng vèo), hệ thống tải lưới tọa độ `route_points` từ CSDL, chiếu điểm GPS hiện hành lên đường đa tuyến (Polyline Projection), sau đó tính tổng độ dài các phân đoạn để ra khoảng cách di chuyển thực tế. Toàn bộ logic nặng nề này được chuyển về **Python Backend** để giảm tải cho phần cứng phía Client.

### 2. Mô hình Push Data với SSE + Redis
Frontend không cần gửi request liên tục (Polling). Khi trang vừa load, nó mở một kênh giao tiếp (`EventSource`). Backend sẽ liên tục quét siêu tốc trên RAM (Redis) và đẩy tọa độ về mỗi 1.5 giây. Nếu có 10,000 người dùng, chỉ có 10,000 socket kết nối ở dạng ngủ chờ nhận data, giúp giảm thiểu overhead của HTTP Headers và CPU ở Backend xuống mức vô cùng nhỏ so với cơ chế truyền thống.

### 3. Auto-Healing Animation trên UI
Giao diện không đơn thuần là xóa Marker cũ và vẽ Marker mới. Hàm `animateMarker()` tích hợp vòng lặp `requestAnimationFrame(60fps)` giúp chiếc xe trượt đi (slide) trên bản đồ một cách tự nhiên. Nếu có nhiễu sóng hoặc lỗi mạng (khoảng cách sai lệch lớn hơn 0.01 độ), thuật toán tự động nhận diện đó là Glitch và hủy Animation để dịch chuyển tức thời (Teleport), đảm bảo đúng thực tế.

---

## 🛣️ Hướng Phát Triển Tiếp Theo (Roadmap)

Dự án đã hoàn chỉnh nền tảng kiến trúc. Trong tương lai có thể mở rộng theo các hướng:
- **Tích hợp Machine Learning:** Sử dụng dữ liệu log lịch sử để huấn luyện mô hình dự đoán trễ chuyến, tính toán trọng số kẹt xe vào thuật toán ETA hiện hành.
- **Scaling Backend:** Triển khai API bằng `FastAPI` với `asyncio` để chịu tải socket tốt hơn nữa.
- **Thêm tính năng Bus Stops Flow:** Mô phỏng số lượng hành khách lên/xuống tại bến.

---

## 👤 Tác Giả

**Nguyễn Hoàng Thiện Anh**
*Realtime Bus Tracking System - Đồ án Hệ thống phân tán & Xử lý Dữ liệu Luồng.*
