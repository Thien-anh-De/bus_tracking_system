# 🚌 Bus Tracking System - Realtime Streaming Pipeline

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-Event_Broker-black.svg)](https://kafka.apache.org/)
[![Spark](https://img.shields.io/badge/Apache_Spark-Stream_Processing-orange.svg)](https://spark.apache.org/)
[![Redis](https://img.shields.io/badge/Redis-In--Memory_State-red.svg)](https://redis.io/)
[![Flask](https://img.shields.io/badge/Flask-SSE_Backend-green.svg)](https://flask.palletsprojects.com/)

**Bus Tracking System** is a full-stack software system that simulates, processes large streaming data, and visualizes bus locations in real-time. Designed with an **Event-driven Architecture** and **Lambda/Kappa concepts**, it features high concurrency handling, highly accurate spatial-based ETA (Estimated Time of Arrival) calculations, and a seamless data pipeline from backend infrastructure to the frontend UI via Server-Sent Events (SSE).

> **Note:** This project is built using production-ready design patterns, demonstrating proficiency in distributed systems, streaming data pipelines, and high-performance Web application architecture. It is ideal for capstone projects, major assignments, or as a strong portfolio piece.

---

## 🎯 Core Problem & Solutions

Intelligent Transport Systems (ITS) frequently face challenges regarding **data latency**, **ETA accuracy**, and **performance bottlenecks** when concurrent map users spike.

This project comprehensively addresses these issues with the following architectural decisions:
1. **Ultra-low Latency Pipeline:** Instead of the frontend constantly polling the relational database, the system uses **Apache Spark** to write real-time state directly into RAM via **Redis**. The **Flask Backend** then uses **SSE (Server-Sent Events)** to push data to the Frontend.
2. **Route-aware ETA Algorithm:** Moving beyond naive straight-line distance, the system projects real-time GPS coordinates onto the polyline matrix of the bus route (Distance-Along-Route algorithm) for highly accurate distance and travel time calculations.
3. **60fps Smooth Animation:** Solves the characteristic coordinate jitter of GPS systems by implementing geometric linear interpolation with easing functions directly on the map interface.

---

## 🏗️ System Architecture

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

## ⚙️ Core Technology Stack

### 1. Data Ingestion & Streaming Pipeline
- **Python Simulator:** A GPS stream simulator generating thousands of events with randomized speeds, adhering to real-world route geometry using the *Haversine* formula.
- **Apache Kafka (Zookeeper):** Serves as the central high-throughput message broker.
- **Apache Spark (Structured Streaming):** Consumes micro-batches from Kafka, normalizes data, and parallelizes writes (Forking).

### 2. Storage & Caching
- **Redis (In-memory Store):** Acts as a *Write-through Cache* for real-time state, entirely eliminating I/O querying pressure on the relational database.
- **PostgreSQL:** Stores catalog data (Routes, Stops) and historical telemetry logs (`bus_gps_log`) for future Data Analytics/Machine Learning purposes.

### 3. API & Presentation Layer
- **Flask (Python API):** Backend providing REST APIs for routing information and spatial ETA calculations. Features long-lived connection endpoints.
- **Server-Sent Events (SSE):** Optimizes web sockets for efficient one-way data pushing from Server to Client.
- **Leaflet.js + OpenStreetMap:** Web GIS system rendering a smooth interactive map.
- **Nginx:** Proxy optimization with buffering disabled to ensure zero-delay SSE streaming.

---

## 🚀 Quick Start

The entire system is containerized. Ensure you have **Docker** and **Docker Compose** installed.

### Step 1: Boot up the infrastructure
```bash
docker-compose up --build -d
```
This command automatically downloads images, configures networks, seeds the database (tables, routes), and starts Kafka, the Spark job, Backend, and Frontend. The initial run may take 2-5 minutes.

### Step 2: Access the system
- **Web Dashboard:** `http://localhost:8080`
- **Backend API (Health check):** `http://localhost:5050/health`
- **Raw SSE Stream:** `http://localhost:5050/api/stream/buses`

### Step 3: Cleanup
```bash
docker-compose down -v
```

---

## 🧠 Technical Highlights

### 1. Advanced ETA Algorithm
Rather than relying on linear Euclidean distance `$D = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$` (which produces massive errors on winding roads), the system loads coordinate grids (`route_points`) from the database, projects the current GPS point onto the polyline (Polyline Projection), and sums the segment lengths for true travel distance. This heavy computational logic is shifted to the **Python Backend** to alleviate hardware strain on the Client side.

### 2. Push Data Model via SSE + Redis
The Frontend no longer sends continuous polling requests. Upon page load, it opens a persistent communication channel (`EventSource`). The Backend continuously performs ultra-fast scans on RAM (Redis) and pushes coordinate updates every 1.5 seconds. For 10,000 concurrent users, the server simply maintains 10,000 sleeping sockets waiting for data, reducing HTTP header overhead and Backend CPU usage to a fraction of traditional mechanisms.

### 3. Auto-Healing UI Animation
The interface does not merely erase the old marker and draw a new one. The `animateMarker()` function integrates a `requestAnimationFrame(60fps)` loop, causing the bus to slide naturally across the map. If signal noise or network errors occur (distance deviation > 0.01 degrees), the algorithm detects the Glitch and cancels the animation for an immediate Teleport, ensuring real-world accuracy.

---

## 🛣️ Roadmap

The architectural foundation is complete. Future expansion paths include:
- **Machine Learning Integration:** Utilizing historical logs to train delay prediction models and incorporate traffic congestion weights into the current ETA algorithm.
- **Backend Scaling:** Migrating the API to `FastAPI` with `asyncio` for even greater socket concurrency handling.
- **Bus Stops Flow Feature:** Simulating passenger boarding/alighting metrics at transit stops.

---

## 👤 Author

**Nguyễn Hoàng Thiện Anh**
*Realtime Bus Tracking System - Distributed Systems & Streaming Data Project.*
