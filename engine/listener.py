import time
import json
import os
import psycopg2
from psycopg2.extras import execute_values
import redis
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

# Konfigurasi Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def get_db_connection():
    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.OperationalError:
            print("🕒 Menunggu database Postgres siap...")
            time.sleep(2)

def start_bulk_listener():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Konfigurasi Batch
    BATCH_LIMIT = 100        # Jumlah data minimal untuk bulk insert
    TIME_THRESHOLD = 30     # Batas waktu (detik) untuk memaksa flush data
    
    buffer = []
    last_flush_time = time.time()

    print(f"🚀 Bulk Listener aktif. Menunggu antrean di Redis...")

    try:
        while True:
            # 1. Ambil data dari list Redis (RPOP mengambil dari ujung antrean)
            raw_data = r.rpop("order_queue")
            
            if raw_data:
                buffer.append(json.loads(raw_data))

            # 2. Cek kondisi untuk Bulk Insert: 
            # Jika buffer penuh ATAU sudah terlalu lama sejak flush terakhir
            current_time = time.time()
            if len(buffer) >= BATCH_LIMIT or (current_time - last_flush_time >= TIME_THRESHOLD and buffer):
                
                try:
                    # Persiapkan data untuk execute_values
                    values = [
                        (
                            b['order_id'], 
                            b['customer_name'], 
                            b['menu_item'], 
                            b['price'], 
                            b['category'], 
                            b['status']
                        ) for b in buffer
                    ]

                    execute_values(cur, """
                        INSERT INTO orders (order_id, customer_name, menu_item, price, category, status)
                        VALUES %s
                        ON CONFLICT (order_id) DO NOTHING
                    """, values)

                    conn.commit()
                    print(f"📦 [BULK INSERT] Berhasil memasukkan {len(buffer)} data ke Postgres.")
                    
                    # Reset buffer dan timer
                    buffer = []
                    last_flush_time = current_time

                except Exception as e:
                    print(f"❌ Gagal melakukan bulk insert: {e}")
                    conn.rollback()
            
            if not raw_data:
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopping Bulk Listener...")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    start_bulk_listener()