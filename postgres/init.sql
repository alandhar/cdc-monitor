-- 1. Membuat Tabel
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) UNIQUE,
    customer_name VARCHAR(100),
    menu_item VARCHAR(100),
    price INT,
    category VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Konfigurasi CDC (Penting agar Trigger terdeteksi)
ALTER TABLE orders REPLICA IDENTITY FULL;

-- 3. Membuat Fungsi Pembersih (Limit 1000 baris)
CREATE OR REPLACE FUNCTION limit_orders_rows()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM orders
    WHERE id NOT IN (
        SELECT id FROM orders
        ORDER BY created_at DESC
        LIMIT 1000
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 4. Membuat Trigger
-- Gunakan DROP TRIGGER IF EXISTS untuk menghindari error saat restart
DROP TRIGGER IF EXISTS trigger_limit_orders ON orders;
CREATE TRIGGER trigger_limit_orders
AFTER INSERT ON orders
FOR EACH STATEMENT
EXECUTE FUNCTION limit_orders_rows();

-- 5. Membuat Publikasi untuk CDC
-- Gunakan DO block agar tidak error jika publikasi sudah ada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'coffee_pub') THEN
        CREATE PUBLICATION coffee_pub FOR ALL TABLES;
    END IF;
END $$;