-- Seed data for examples/postgres.yaml and compose run-postgres-example.
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

INSERT INTO orders (id, name, status, amount, updated_at) VALUES
    (1, 'Alice', 'active', 100, '2099-01-01 00:00:00'),
    (2, 'Bob', 'inactive', 200, '2099-01-01 00:00:00'),
    (3, 'Charlie', 'active', 50, '2099-01-01 00:00:00');
