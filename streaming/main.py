import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, row_number
from pyspark.sql.window import Window

from schemas import get_gps_schema
from spark_reader import read_kafka_stream
from redis_store import RedisStore

# =====================================================
# CONFIG
# =====================================================
DB_HOST = "postgres"
DB_PORT = "5432"
DB_NAME = "bus_tracking_system"
DB_USER = "bus_user"
DB_PASS = "Thienanh1906@"

KAFKA_SERVERS = "kafka:9093"
KAFKA_TOPIC = "bus_location"

JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_PROPERTIES = {
    "user": DB_USER,
    "password": DB_PASS,
    "driver": "org.postgresql.Driver"
}

CHECKPOINT_PATH = "/app/checkpoints/bus_tracking"

# =====================================================
# SPARK SESSION
# =====================================================
spark = (
    SparkSession.builder
    .appName("BusStreaming-STABLE-FINAL")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
        "org.postgresql:postgresql:42.6.0"
    )
    .config("spark.sql.shuffle.partitions", "1")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

redis_store = RedisStore(host="redis")

# =====================================================
# READ KAFKA
# =====================================================
schema = get_gps_schema()

stream_df = read_kafka_stream(
    spark,
    KAFKA_SERVERS,
    KAFKA_TOPIC,
    schema
)

# =====================================================
# PROCESS BATCH
# =====================================================
def process_batch(batch_df, batch_id):
    if batch_df.isEmpty():
        return

    print(f"\n🚀 Processing batch {batch_id}")

    # -------------------------------------------------
    # 1. PARSE + CHUẨN HÓA DATA
    # -------------------------------------------------
    base_df = (
        batch_df
        .withColumn(
            "ts",
            to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        )
        .select(
            col("bus_id").cast("string").alias("bus_id"),
            col("lat").cast("double"),
            col("lon").cast("double"),
            col("speed").cast("int"),
            col("direction").cast("int"),
            col("ts")
        )
        .filter(col("ts").isNotNull())
        .cache()
    )

    # -------------------------------------------------
    # 2. REDIS – REALTIME MAP
    # -------------------------------------------------
    redis_store.save_location_batch(base_df.collect())

    # -------------------------------------------------
    # 3. GPS LOG (APPEND OK)
    # -------------------------------------------------
    base_df.write.jdbc(
        url=JDBC_URL,
        table="bus_gps_log",
        mode="append",
        properties=DB_PROPERTIES
    )

    # -------------------------------------------------
    # 4. CURRENT STATUS (LẤY BẢN GHI MỚI NHẤT MỖI XE)
    # -------------------------------------------------
    w = Window.partitionBy("bus_id").orderBy(col("ts").desc())

    latest_df = (
        base_df
        .withColumn("rn", row_number().over(w))
        .filter(col("rn") == 1)
        .select(
            "bus_id",
            "lat",
            "lon",
            "speed",
            "direction",
            col("ts").alias("last_update")
        )
    )

    # 👉 GHI VÀO BẢNG TẠM
    temp_table = "bus_current_status_tmp"

    latest_df.write.jdbc(
        url=JDBC_URL,
        table=temp_table,
        mode="overwrite",
        properties=DB_PROPERTIES
    )

    # 👉 UPSERT BẰNG SQL (QUAN TRỌNG)
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO bus_current_status
        (bus_id, lat, lon, speed, direction, last_update)
        SELECT bus_id, lat, lon, speed, direction, last_update
        FROM bus_current_status_tmp
        ON CONFLICT (bus_id) DO UPDATE SET
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            speed = EXCLUDED.speed,
            direction = EXCLUDED.direction,
            last_update = EXCLUDED.last_update
    """)

    conn.commit()
    cur.close()
    conn.close()

    base_df.unpersist()

# =====================================================
# START STREAM
# =====================================================
query = (
    stream_df.writeStream
    .foreachBatch(process_batch)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .start()
)

query.awaitTermination()
