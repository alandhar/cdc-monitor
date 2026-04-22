import psycopg2
import time
import random
import json
from faker import Faker
import os
import string
import datetime
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi Faker untuk nama pelanggan
fake = Faker()

# Konfigurasi Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# Menu Coffee Shop Bandung
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "menu_coffeeshop.json")
with open(file_path, "r") as f:
    MENU = json.load(f)

def get_connection():
    while True:
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.OperationalError:
            print("🕒 Menunggu database siap...")
            time.sleep(2)

def generate_order_id():
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CB-{date_str}-{random_str}"

def simulate_transactions():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM orders WHERE status IN ('pending', 'on process')")
    active_order_ids = [row[0] for row in cur.fetchall()]
    print(f"🚀 Generator kembali aktif. Melanjutkan {len(active_order_ids)} pesanan yang tertunda.")
    
    try:
        while True:
            # Tentukan aksi secara acak: 70% Insert, 25% Update, 5% Delete
            action_roll = random.random()

            # 1. INSERT: Pesanan Baru
            if action_roll < 0.7 or not active_order_ids:
                item = random.choice(MENU)
                name = fake.name()
                custom_id = generate_order_id()
                
                cur.execute(
                    """
                    INSERT INTO orders (order_id, customer_name, menu_item, price, category, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (order_id) DO NOTHING
                    RETURNING id
                    """,
                    (custom_id, name, item['name'], item['price'], item['category'], 'pending')
                )
                result = cur.fetchone()
                
                if result:
                    new_db_id = result[0]
                    active_order_ids.append(new_db_id)
                    print(f"[INSERT] Order #{custom_id}: {name} memesan {item['name']}")
                else:
                    print(f"⚠️ Skip: Order ID {custom_id} sudah ada, mencoba lagi di loop berikutnya.")

            # 2. UPDATE: Perubahan Status (dari pending -> on process -> completed)
            elif action_roll < 0.95:
                db_id = random.choice(active_order_ids)
                new_status = random.choice(['on process', 'completed'])
                
                cur.execute(
                    "UPDATE orders SET status = %s WHERE id = %s RETURNING order_id", 
                    (new_status, db_id)
                )
                actual_custom_id = cur.fetchone()[0]
                print(f"[UPDATE] Order #{actual_custom_id} status berubah menjadi: {new_status}")
                
                if new_status == 'completed':
                    active_order_ids.remove(db_id)

            # 3. UPDATE: Pembatalan Pesanan
            else:
                db_id = random.choice(active_order_ids)
                cur.execute(
                    "UPDATE orders SET status = 'cancelled' WHERE id = %s RETURNING order_id", 
                    (db_id,)
                )
                actual_custom_id = cur.fetchone()[0]
                active_order_ids.remove(db_id)
                print(f"[UPDATE] Order #{actual_custom_id} dibatalkan oleh pelanggan")

            # Beri jeda acak 1-5 detik agar terlihat natural
            time.sleep(random.uniform(1, 5))

    except KeyboardInterrupt:
        print("\nStopping generator...")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    simulate_transactions()