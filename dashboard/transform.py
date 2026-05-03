import os
import time
import requests
import json
import pandas as pd

from utils.logger import setup_logger
logger = setup_logger()

URL_API = os.getenv("URL_API", "http://localhost:5001/api/v1/stream")
RECONNECT_DELAY = 3   # detik sebelum mencoba reconnect

class DataTransformer:
    def __init__(self):
        # Database lokal sementara untuk menyimpan state pesanan
        self.orders_cache = {}

    def get_stream_data(self):
        """Generator untuk mengambil data dari API stream secara terus-menerus"""
        while True:
            try:
                logger.info(f"🔌 Menghubungkan ke SSE stream: {URL_API}")
                response = requests.get(URL_API, stream=True, timeout=(5, None))
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8') if isinstance(line, bytes) else line
                        if decoded_line.startswith("data: "):
                            json_str = decoded_line[len("data: "):]   # lebih aman dari .replace()
                            raw_data = json.loads(json_str)
                            
                            # Simpan/Update data ke dalam cache berdasarkan order_id
                            self.orders_cache[raw_data['order_id']] = raw_data
                            
                            # Kirim seluruh cache yang sudah jadi DataFrame ke UI
                            yield pd.DataFrame(self.orders_cache.values())

            except requests.exceptions.ConnectionError:
                logger.warning(f"⚠️  Koneksi ke API gagal. Retry dalam {RECONNECT_DELAY}s...")
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️  Koneksi timeout. Retry dalam {RECONNECT_DELAY}s...")
            except Exception as e:
                logger.error(f"❌ Error stream: {e}. Retry dalam {RECONNECT_DELAY}s...")

            time.sleep(RECONNECT_DELAY)