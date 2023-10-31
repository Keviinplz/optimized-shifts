DROP TABLE IF EXISTS places, travels;

CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE travels (
    id SERIAL PRIMARY KEY,
    region TEXT NOT NULL,
    origin POINT NOT NULL,
    destination POINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source TEXT
);