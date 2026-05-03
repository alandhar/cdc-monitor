FROM python:3.11-slim

WORKDIR /app

# Install dependensi terlebih dahulu (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh project (dibutuhkan untuk utils/ dan dashboard/)
COPY . .

# Port Gradio
EXPOSE 7860

# Jalankan dashboard dari root project agar import utils.logger bekerja
CMD ["python", "dashboard/main.py"]