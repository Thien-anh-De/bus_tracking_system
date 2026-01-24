FROM apache/spark:3.5.0

USER root

# Cài pip + python deps
RUN python3 -m pip install --upgrade pip && \
    pip install --no-cache-dir \
        psycopg2-binary==2.9.9 \
        redis==5.0.1

# Quay lại user mặc định
USER 185
