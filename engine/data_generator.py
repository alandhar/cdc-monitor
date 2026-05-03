import os
import sys
import time
import json
import redis
import random
import string
import datetime
from faker import Faker
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))               # tambah folder dashboard (untuk transform)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # tambah root project (untuk utils)

from dotenv import load_dotenv
load_dotenv()

from utils.logger import setup_logger
logger = setup_logger()

fake = Faker()

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST"),
    "port": int(os.getenv("REDIS_PORT")),
    "decode_responses": True
}

# Menu Coffee Shop
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
            logger.info("🕒 Menunggu Redis siap...")
            time.sleep(2)

def send_event(r, order_data):
    payload = json.dumps(order_data)

    r.lpush("order_queue", payload)                 # Batch Insert to DB
    r.publish("coffee_orders_channel", payload)     # Real-time update for API

    # logger.info(f"[EVENT] {order_data['order_id']} | {order_data['status']} \n        {order_data['customer_name']} ordered {order_data['menu_item']}\n")

def generate_order_id():
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CB-{date_str}-{random_str}"

def process_order_lifecycle(r, base_order):
    # ---------------- New Order Pending ----------------
    order_data = {**base_order, "status": "pending"}
    send_event(r, order_data)

    time.sleep(random.uniform(0.5, 1.5))

    # ---------------- Order Cancelled ----------------
    if random.random() < 0.2:   # 20% chance of cancellation
        order_data = {**base_order, "status": "cancelled"}
        send_event(r, order_data)
        return
    
    # ---------------- Order On Process ----------------
    order_data = {**base_order, "status": "on_process"}
    send_event(r, order_data)

    time.sleep(random.uniform(1, 2))

    # ---------------- Order Completed ----------------
    order_data = {**base_order, "status": "complete"}
    send_event(r, order_data)

def simulate_transactions():
    r = get_redis_connection()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        try:
            while True:
                item = random.choice(MENU)
                name = fake.name()
                order_id = generate_order_id()
                
                base_order = {
                    "order_id": order_id,
                    "customer_name": name,
                    "menu_item": item['name'],
                    "price": item['price'],
                    "category": item['category'],
                    "timestamp": datetime.datetime.now().isoformat()
                }

                executor.submit(process_order_lifecycle, r, base_order)
                time.sleep(random.uniform(0.5, 1.5))

        except KeyboardInterrupt:
            logger.info("\nStopping generator...")

if __name__ == "__main__":
    simulate_transactions()