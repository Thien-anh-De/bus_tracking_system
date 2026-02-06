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
    # 1. PARSE TIMESTAMP (GIỮ ts CHO REDIS)
    # -------------------------------------------------
    base_df = (
        batch_df
        .withColumn(
            "ts",
            to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        )
        .select(
            col("bus_id").cast("string").alias("bus_id"),
            col("lat"),
            col("lon"),
            col("speed"),
            col("direction"),
            col("ts")
        )
        .cache()
    )

    # -------------------------------------------------
    # 2. REDIS (REALTIME MAP) – FIX LỖI ts
    # -------------------------------------------------
    redis_store.save_location_batch(base_df.collect())

    # -------------------------------------------------
    # 3. GPS LOG
    # -------------------------------------------------
    base_df.write.jdbc(
        url=JDBC_URL,
        table="bus_gps_log",
        mode="append",
        properties=DB_PROPERTIES
    )

    # -------------------------------------------------
    # 4. CURRENT STATUS
    # -------------------------------------------------
    w = Window.partitionBy("bus_id").orderBy(col("ts").desc())

    status_df = (
        base_df
        .withColumn("rn", row_number().over(w))
        .filter(col("rn") == 1)
        .select(
            "bus_id",
            "lat",
            "lon",
            "speed",
            "direction",
            col("ts").alias("last_update")   # ⭐ map ts → last_update
        )
    )

    status_df.write.jdbc(
        url=JDBC_URL,
        table="bus_current_status",
        mode="overwrite",
        properties=DB_PROPERTIES
    )

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
