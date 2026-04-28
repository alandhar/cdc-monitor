import logging
import os
import json
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    Formatter kustom untuk mengubah log menjadi format JSON.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "name": record.name,  # Ini akan otomatis mendeteksi nama file/module
            "message": record.getMessage(),
            "func_name": record.funcName,
            "line_no": record.lineno
        }
        return json.dumps(log_record)

def setup_logger(name=None):
    """
    Fungsi untuk inisialisasi logger di setiap file.
    """
    frame = inspect.stack()[1]
    caller_path = frame.filename 
    caller_filename = os.path.splitext(os.path.basename(caller_path))[0]
    
    caller_dir = os.path.basename(os.path.dirname(caller_path))

    if name is None:
        name = caller_filename

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Handler untuk File (Limitasi: 2MB per file, simpan 2 file terakhir saja)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{caller_filename}.json.log"),
            maxBytes=2 * 1024 * 1024,
            backupCount=2
        )
        file_handler.setFormatter(JsonFormatter())

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            f'%(asctime)s - [%(levelname)s] ({caller_dir}/%(name)s): %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger