import psycopg2
import time
import random
import json
from faker import Faker
import os
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

def simulate_transactions():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    print("🚀 Generator aktif... Mengirim transaksi ke Postgres.")

    active_order_ids = []

    try:
        while True:
            # Tentukan aksi secara acak: 70% Insert, 25% Update, 5% Delete
            action_roll = random.random()

            # 1. INSERT: Pesanan Baru
            if action_roll < 0.7 or not active_order_ids:
                item = random.choice(MENU)
                name = fake.name()
                cur.execute(
                    """
                    INSERT INTO orders (customer_name, menu_item, price, category, status)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, item['name'], item['price'], item['category'], 'pending')
                )
                new_id = cur.fetchone()[0]
                active_order_ids.append(new_id)
                print(f"[INSERT] Order #{new_id}: {name} memesan {item['name']}")

            # 2. UPDATE: Perubahan Status (dari pending -> on process -> completed)
            elif action_roll < 0.95:
                order_id = random.choice(active_order_ids)
                new_status = random.choice(['on process', 'completed'])
                
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
                print(f"[UPDATE] Order #{order_id} status berubah menjadi: {new_status}")
                
                if new_status == 'completed':
                    active_order_ids.remove(order_id)

            # 3. UPDATE: Pembatalan Pesanan
            else:
                order_id = random.choice(active_order_ids)
                new_status = 'cancelled'
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
                active_order_ids.remove(order_id)
                print(f"[UPDATE] Order #{order_id} dibatalkan oleh pelanggan")

            # Beri jeda acak 1-5 detik agar terlihat natural
            time.sleep(random.uniform(1, 5))

    except KeyboardInterrupt:
        print("\nStopping generator...")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    simulate_transactions()