CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100),
    menu_item VARCHAR(100),
    price INT,
    category VARCHAR(50),
    status VARCHAR(20), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Membuat publikasi untuk semua tabel agar log-nya dicatat
CREATE PUBLICATION coffee_pub FOR ALL TABLES;