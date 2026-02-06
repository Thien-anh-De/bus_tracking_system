FROM python:3.11-slim

WORKDIR /app

# Cài thư viện hệ thống cho psycopg2
RUN apt-get update \
    && apt-get install -y libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY main.py .

# 🔥 TẮT BUFFER STDOUT
ENV PYTHONUNBUFFERED=1

# Chạy cleaner
CMD ["python", "main.py"]
