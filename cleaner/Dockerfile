FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt thư viện hệ thống cần thiết cho psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy và cài đặt thư viện python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn
COPY main.py .

# Chạy script
CMD ["python", "main.py"]