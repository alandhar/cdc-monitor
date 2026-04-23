import os
import json
import redis
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kopi-bandung-secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Konfigurasi Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

def redis_listener():
    """Fungsi untuk mendengarkan pesan dari Redis Pub/Sub secara background"""
    pubsub = r.pubsub()
    pubsub.subscribe("coffee_orders_channel")
    
    print("📡 Flask Listener aktif, menunggu pesan dari Redis...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # Kirim data ke semua client yang terkoneksi ke WebSocket
            socketio.emit('new_order', data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders')
def get_orders():
    # Mengambil 10 data terbaru dari antrean Redis (order_queue)
    raw_orders = r.lrange("order_queue", 0, 9)
    orders = [json.loads(order) for order in raw_orders]
    
    return jsonify({
        "status": "success",
        "total": len(orders),
        "data": orders
    })

if __name__ == '__main__':
    # Jalankan listener Redis di thread terpisah agar tidak memblokir Flask
    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()
    
    # Jalankan Flask-SocketIO
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)