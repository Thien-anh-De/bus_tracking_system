CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    route_name TEXT,
    start_point TEXT,
    end_depot TEXT
);
CREATE TABLE stops (
    stop_id SERIAL PRIMARY KEY,
    stop_name TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);
CREATE TABLE route_stops (
    route_id INT,
    stop_id INT,
    stop_order INT,
    PRIMARY KEY (route_id, stop_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);
CREATE TABLE buses (
    bus_id VARCHAR(10) PRIMARY KEY,
    route_id INT,
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);
CREATE TABLE bus_current_status (
    bus_id VARCHAR(10) PRIMARY KEY,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    last_update TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
);
CREATE TABLE bus_gps_log (
    id SERIAL PRIMARY KEY,
    bus_id VARCHAR(10),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed INT,
    ts TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
);
