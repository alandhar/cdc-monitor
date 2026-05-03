import os
import sys
import json
import redis
import threading
from flask_socketio import SocketIO
from flask import Flask, Response, stream_with_context, Blueprint, jsonify

sys.path.insert(0, os.path.dirname(__file__))               # tambah folder dashboard (untuk transform)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # tambah root project (untuk utils)

from dotenv import load_dotenv
load_dotenv()

from utils.logger import setup_logger
logger = setup_logger()

app = Flask(__name__)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

def redis_listener():
    """Fungsi untuk mendengarkan pesan dari Redis Pub/Sub secara background"""
    pubsub = r.pubsub()
    pubsub.subscribe("coffee_orders_channel")
    
    logger.info("📡 Flask Listener aktif, menunggu pesan dari Redis...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # Kirim data ke semua client yang terkoneksi ke WebSocket
            socketio.emit('new_order', data)

@api_v1.route('/stream')
def stream():
    def event_stream():
        try:
            pubsub = r.pubsub()
            pubsub.subscribe("coffee_orders_channel")
            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Data dari Redis sudah berupa string JSON, kirim langsung
                    yield f"data: {message['data']}\n"
        except Exception as e:
            logger.error(f"Stream Error: {e}")
        finally:
            pubsub.close()
            logger.info("PubSub connection closed safely.")

    # Set header yang diperlukan agar SSE berfungsi dengan benar di browser/client
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',       # Matikan buffering di nginx
        'Access-Control-Allow-Origin': '*',
    }
    return Response(
        stream_with_context(event_stream()),
        headers=headers
    )

@api_v1.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "service": "coffee-cdc-monitor"
    }), 200

app.register_blueprint(api_v1)

if __name__ == '__main__':
    # Jalankan listener Redis di thread terpisah agar tidak memblokir Flask
    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()
    
    # Jalankan Flask-SocketIO dengan threading mode
    # allow_unsafe_werkzeug=True diperlukan untuk dev server di mode threading
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)