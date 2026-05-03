import requests
import json
import pandas as pd

from utils.logger import setup_logger
logger = setup_logger()

URL_API = "http://localhost:5001/api/v1/stream"

class DataTransformer:
    def __init__(self):
        # Database lokal sementara untuk menyimpan state pesanan
        self.orders_cache = {}

    def get_stream_data(self):
        """Generator untuk mengambil data dari API stream secara terus-menerus"""
        try:
            # Gunakan stream=True agar koneksi HTTP tetap terbuka
            response = requests.get(URL_API, stream=True, timeout=10)
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line.replace("data: ", "")
                        raw_data = json.loads(json_str)
                        
                        # Simpan/Update data ke dalam cache berdasarkan order_id
                        # Ini otomatis menangani perubahan status (pending -> complete)
                        self.orders_cache[raw_data['order_id']] = raw_data
                        
                        # Kirim seluruh cache yang sudah jadi DataFrame ke UI
                        yield pd.DataFrame(self.orders_cache.values())
        except Exception as e:
            logger.error(f"Error connecting to stream: {e}")