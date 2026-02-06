-- ==========================================================
-- PHẦN 1: CLEANUP
-- ==========================================================
DROP TABLE IF EXISTS bus_stop_events CASCADE;
DROP TABLE IF EXISTS bus_gps_log CASCADE;
DROP TABLE IF EXISTS staging_bus_status CASCADE;
DROP TABLE IF EXISTS bus_current_status CASCADE;
DROP TABLE IF EXISTS route_stops CASCADE;
DROP TABLE IF EXISTS route_points CASCADE;
DROP TABLE IF EXISTS buses CASCADE;
DROP TABLE IF EXISTS stops CASCADE;
DROP TABLE IF EXISTS routes CASCADE;

-- ==========================================================
-- PHẦN 2: SCHEMA
-- ==========================================================

-- 1. Routes
CREATE TABLE routes (
    route_id INT PRIMARY KEY,
    route_name TEXT,
    start_point TEXT,
    end_depot TEXT
);

-- 2. Stops
CREATE TABLE stops (
    stop_id INT PRIMARY KEY,
    stop_name TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);

-- 3. Route - Stops
CREATE TABLE route_stops (
    route_id INT,
    stop_id INT,
    stop_order INT,
    PRIMARY KEY (route_id, stop_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- 4. Buses
CREATE TABLE buses (
    bus_id VARCHAR(10) PRIMARY KEY,
    route_id INT,
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

-- 5. Route points (geometry truth)
CREATE TABLE route_points (
    id SERIAL PRIMARY KEY,
    route_id INT NOT NULL,
    point_order INT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    CONSTRAINT uq_route_point UNIQUE (route_id, point_order)
);

-- 6. GPS log
CREATE TABLE bus_gps_log (
    id SERIAL PRIMARY KEY,
    bus_id VARCHAR(10),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    direction INT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
);

-- 7. Stop events
CREATE TABLE bus_stop_events (
    id SERIAL PRIMARY KEY,
    bus_id VARCHAR(10),
    stop_id INT,
    arrived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    distance_m DOUBLE PRECISION,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- 8. Current status (⭐ KHÔNG ALTER THÊM)
CREATE TABLE bus_current_status (
    bus_id VARCHAR(10) PRIMARY KEY,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    direction INT,
    last_update TIMESTAMP
);
