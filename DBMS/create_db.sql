-- ================= CLEANUP =================
DROP TABLE IF EXISTS bus_stop_events CASCADE;
DROP TABLE IF EXISTS bus_gps_log CASCADE;
DROP TABLE IF EXISTS bus_current_status CASCADE;
DROP TABLE IF EXISTS route_stops CASCADE;
DROP TABLE IF EXISTS route_points CASCADE;
DROP TABLE IF EXISTS buses CASCADE;
DROP TABLE IF EXISTS stops CASCADE;
DROP TABLE IF EXISTS routes CASCADE;

-- ================= ROUTES =================
CREATE TABLE routes (
    route_id INT PRIMARY KEY,
    route_name TEXT,
    start_point TEXT,
    end_depot TEXT
);

-- ================= STOPS =================
CREATE TABLE stops (
    stop_id INT PRIMARY KEY,
    stop_name TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);

-- ================= ROUTE_STOPS =================
CREATE TABLE route_stops (
    route_id INT REFERENCES routes(route_id),
    stop_id INT REFERENCES stops(stop_id),
    stop_order INT,
    PRIMARY KEY (route_id, stop_id)
);

-- ================= BUSES =================
CREATE TABLE buses (
    bus_id VARCHAR(10) PRIMARY KEY,
    route_id INT REFERENCES routes(route_id)
);

-- ================= ROUTE_POINTS =================
CREATE TABLE route_points (
    id SERIAL PRIMARY KEY,
    route_id INT REFERENCES routes(route_id),
    point_order INT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    UNIQUE (route_id, point_order)
);

-- ================= GPS LOG =================
CREATE TABLE bus_gps_log (
    id SERIAL PRIMARY KEY,
    bus_id VARCHAR(10) REFERENCES buses(bus_id),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    direction INT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================= STOP EVENTS =================
CREATE TABLE bus_stop_events (
    id SERIAL PRIMARY KEY,
    bus_id VARCHAR(10) REFERENCES buses(bus_id),
    stop_id INT REFERENCES stops(stop_id),
    trip_id INT,
    arrived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    distance_m DOUBLE PRECISION
);

-- ================= CURRENT STATUS =================
CREATE TABLE bus_current_status (
    bus_id VARCHAR(10) PRIMARY KEY,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    direction INT,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
