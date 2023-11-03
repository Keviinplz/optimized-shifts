DROP TABLE IF EXISTS regions, trips;

CREATE TABLE regions (
    region_id INT GENERATED ALWAYS AS IDENTITY,
    region_name VARCHAR(50) UNIQUE NOT NULL,
    PRIMARY KEY (region_id)
);

CREATE TABLE trips (
    trip_id INT GENERATED ALWAYS AS IDENTITY,
    region_id INT,
    origin POINT NOT NULL,
    destination POINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source TEXT,
    PRIMARY KEY (trip_id),
    CONSTRAINT fk_region
        FOREIGN KEY(region_id)
            REFERENCES regions(region_id)
);

