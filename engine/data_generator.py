import time
import random
import json
from faker import Faker
import os
import string
import datetime
import redis
from dotenv import load_dotenv

load_dotenv()

fake = Faker()

# Konfigurasi Redis
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST"),
    "port": int(os.getenv("REDIS_PORT")),
    "decode_responses": True
}

# Menu Coffee Shop Bandung
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "menu_coffeeshop.json")
with open(file_path, "r") as f:
    MENU = json.load(f)

def get_redis_connection():
    while True:
        try:
            r = redis.Redis(**REDIS_CONFIG)
            if r.ping():
                return r
        except redis.ConnectionError:
            print("🕒 Menunggu Redis siap...")
            time.sleep(2)

def generate_order_id():
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CB-{date_str}-{random_str}"

def simulate_transactions():
    r = get_redis_connection()
    print(f"🚀 Generator aktif. Mengirim data ke Redis Host: {REDIS_CONFIG['host']}")
    
    try:
        while True:
            item = random.choice(MENU)
            name = fake.name()
            order_id = generate_order_id()
            
            order_data = {
                "order_id": order_id,
                "customer_name": name,
                "menu_item": item['name'],
                "price": item['price'],
                "category": item['category'],
                "status": "pending",
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            payload = json.dumps(order_data)

            # 1. Masukkan ke Antrean (Buffer untuk Bulk Insert nantinya)
            r.lpush("order_queue", payload)

            # 2. Publish ke Channel (Untuk Real-time Dashboard)
            r.publish("coffee_orders_channel", payload)

            print(f"[SENT TO REDIS] {order_id} | {name} memesan {item['name']}")

            # Jeda acak 1-3 detik (lebih cepat sedikit untuk ngetes antrean)
            time.sleep(random.uniform(1, 3))

    except KeyboardInterrupt:
        print("\nStopping generator...")

if __name__ == "__main__":
    simulate_transactions()