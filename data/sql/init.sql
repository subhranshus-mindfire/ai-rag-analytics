-- Initialize Schema for Analytics & Text-to-SQL

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    segment VARCHAR(50) DEFAULT 'Standard',
    country VARCHAR(50) DEFAULT 'United States',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'completed', -- completed, pending, cancelled, refunded
    total_amount NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

-- Seed Initial Data
INSERT INTO customers (name, email, segment, country) VALUES
('Alice Johnson', 'alice@example.com', 'Enterprise', 'United States'),
('Bob Smith', 'bob@example.com', 'SMB', 'Canada'),
('Charlie Brown', 'charlie@example.com', 'Consumer', 'United Kingdom'),
('Diana Prince', 'diana@example.com', 'Enterprise', 'United States'),
('Evan Wright', 'evan@example.com', 'SMB', 'Germany');

INSERT INTO products (name, category, price, stock_quantity) VALUES
('AI Analytics Dashboard', 'Software', 499.00, 100),
('Cloud Vector Engine Pro', 'Software', 999.00, 50),
('Developer API Seat', 'Subscription', 49.00, 500),
('Hardware Security Key', 'Hardware', 75.00, 200),
('Enterprise Support SLA', 'Services', 1500.00, 20);

INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES
(1, '2026-09-01 10:15:00', 'completed', 1498.00),
(2, '2026-09-05 14:30:00', 'completed', 49.00),
(3, '2026-09-12 09:00:00', 'completed', 150.00),
(4, '2026-09-18 16:45:00', 'completed', 2499.00),
(1, '2026-09-22 11:20:00', 'completed', 999.00),
(5, '2026-09-25 13:10:00', 'refunded', 499.00),
(2, '2026-09-28 17:00:00', 'pending', 49.00);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 499.00),
(1, 2, 1, 999.00),
(2, 3, 1, 49.00),
(3, 4, 2, 75.00),
(4, 2, 1, 999.00),
(4, 5, 1, 1500.00),
(5, 2, 1, 999.00),
(6, 1, 1, 499.00),
(7, 3, 1, 49.00);
