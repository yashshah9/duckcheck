-- Seed data for examples/mysql.yaml and compose run-mysql-example.
CREATE TABLE orders (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

INSERT INTO orders (id, name, status, amount, updated_at) VALUES
    (1, 'Alice', 'active', 100, '2030-01-01 00:00:00'),
    (2, 'Bob', 'inactive', 200, '2030-01-01 00:00:00'),
    (3, 'Charlie', 'active', 50, '2030-01-01 00:00:00');
