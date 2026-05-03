import os
import sys
import time
import json
import redis
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.dirname(__file__))               # tambah folder dashboard (untuk transform)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # tambah root project (untuk utils)

from dotenv import load_dotenv
load_dotenv()

from utils.logger import setup_logger
logger = setup_logger()

def get_redis_connection():
    while True:
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST"),
                port=int(os.getenv("REDIS_PORT")),
                decode_responses=True
            )
            if r.ping():
                logger.info("✅ Redis terhubung.")
                return r
        except redis.ConnectionError:
            logger.info("🕒 Menunggu Redis siap...")
            time.sleep(2)

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
            logger.info("🕒 Menunggu database Postgres siap...")
            time.sleep(2)

def start_bulk_listener():
    r = get_redis_connection()   # FIX 1: gunakan fungsi retry
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Konfigurasi Batch
    BATCH_LIMIT = 100        # Jumlah data minimal untuk bulk insert
    TIME_THRESHOLD = 30     # Batas waktu (detik) untuk memaksa flush data
    
    buffer = []
    last_flush_time = time.time()

    logger.info(f"🚀 Bulk Listener aktif. Menunggu antrean di Redis...")

    try:
        while True:
            # 1. Ambil data dari list Redis (RPOP mengambil dari ujung antrean)
            raw_data = r.rpop("order_queue")
            
            if raw_data:
                buffer.append(json.loads(raw_data))

            latest_records = {}
            for record in buffer:
                latest_records[record['order_id']] = record

            deduped_buffer = list(latest_records.values())

            # 2. Cek kondisi untuk Bulk Insert: 
            # Jika buffer penuh ATAU sudah terlalu lama sejak flush terakhir
            current_time = time.time()
            if len(deduped_buffer) >= BATCH_LIMIT or (current_time - last_flush_time >= TIME_THRESHOLD and deduped_buffer):
                
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
                        ) for b in deduped_buffer
                    ]

                    execute_values(cur, """
                        INSERT INTO orders (
                            order_id, customer_name, menu_item, price, category, status
                        )
                        VALUES %s
                        ON CONFLICT (order_id)
                        DO UPDATE SET
                            customer_name = EXCLUDED.customer_name,
                            menu_item = EXCLUDED.menu_item,
                            price = EXCLUDED.price,
                            category = EXCLUDED.category,
                            status = EXCLUDED.status,
                            updated_at = CURRENT_TIMESTAMP
                    """, values)

                    conn.commit()
                    # logger.info(f"📦 [BULK INSERT] Berhasil memasukkan {len(deduped_buffer)} data ke Postgres.")
                    
                    # Reset buffer dan timer
                    buffer = []
                    last_flush_time = current_time

                except Exception as e:
                    logger.error(f"❌ Gagal melakukan bulk insert: {e}")
                    conn.rollback()
            
            if not raw_data:
                time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("\nStopping Bulk Listener...")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    start_bulk_listener()