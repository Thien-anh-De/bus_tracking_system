import os
import math

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_timestamp, current_timestamp, udf, broadcast, row_number
)
from pyspark.sql.types import DoubleType
from pyspark.sql.window import Window

from schemas import get_gps_schema
from spark_reader import read_kafka_stream
from redis_store import RedisStore


# ========= 0. CẤU HÌNH =========
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bus_tracking_system")
DB_USER = os.getenv("DB_USER", "bus_user")
DB_PASS = os.getenv("DB_PASSWORD", "Thienanh1906@")

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "kafka:9093")

JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_PROPERTIES = {
    "user": DB_USER,
    "password": DB_PASS,
    "driver": "org.postgresql.Driver"
}

KAFKA_TOPIC = "bus_location"
CHECKPOINT_PATH = "/tmp/bus_tracking_checkpoint"


# ========= 1. SPARK SESSION =========
spark = (
    SparkSession.builder
    .appName("BusRealtimeStreaming")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
        "org.postgresql:postgresql:42.6.0"
    )
    .config("spark.sql.streaming.checkpointLocation", "/app/checkpoints")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ========= 2. READ STREAM =========
schema = get_gps_schema()
redis_store = RedisStore(host="redis")

stream_df = read_kafka_stream(
    spark, KAFKA_SERVERS, KAFKA_TOPIC, schema
)


# ========= 3. LOAD STOPS =========
stops_df = spark.read.jdbc(
    url=JDBC_URL,
    table="stops",
    properties=DB_PROPERTIES
).select(
    col("stop_id"),
    col("lat").alias("stop_lat"),
    col("lon").alias("stop_lon")
)

stops_df = broadcast(stops_df)


# ========= 4. HAVERSINE =========
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(dlambda / 2) ** 2

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


haversine_udf = udf(haversine, DoubleType())


# ========= 5. PROCESS BATCH =========
def process_batch(batch_df, batch_id):
    if batch_df.isEmpty():
        return

    print(f"🚀 Processing Batch {batch_id}")

    # A. Ép kiểu thời gian
    processed_df = batch_df.withColumn(
        "ts_casted",
        to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
    ).cache()

    # B. Redis
    redis_store.save_location_batch(processed_df.collect())

    # C. GPS LOG
    processed_df.select(
        "bus_id", "lat", "lon", "speed",
        col("ts_casted").alias("ts")
    ).write.jdbc(
        url=JDBC_URL,
        table="bus_gps_log",
        mode="append",
        properties=DB_PROPERTIES
    )

    # ========= D. CURRENT STATUS =========
    window_spec = Window.partitionBy("bus_id").orderBy(col("ts_casted").desc())

    status_df = processed_df \
        .withColumn("rn", row_number().over(window_spec)) \
        .filter(col("rn") == 1) \
        .select(
            "bus_id",
            "lat",
            "lon",
            "speed",
            col("ts_casted").alias("last_update")
        )

    status_df.write.jdbc(
        url=JDBC_URL,
        table="staging_bus_status",
        mode="overwrite",
        properties=DB_PROPERTIES
    )

    merge_sql = """
    MERGE INTO public.bus_current_status t
    USING public.staging_bus_status s
    ON t.bus_id = s.bus_id
    WHEN MATCHED THEN
      UPDATE SET
        lat = s.lat,
        lon = s.lon,
        speed = s.speed,
        last_update = s.last_update
    WHEN NOT MATCHED THEN
      INSERT (bus_id, lat, lon, speed, last_update)
      VALUES (s.bus_id, s.lat, s.lon, s.speed, s.last_update);
    """

    conn = spark._sc._gateway.jvm.java.sql.DriverManager.getConnection(
        JDBC_URL,
        DB_PROPERTIES["user"],
        DB_PROPERTIES["password"]
    )
    stmt = conn.createStatement()
    stmt.execute(merge_sql)
    stmt.close()
    conn.close()

    # ========= E. ⭐ PHÁT HIỆN XE TỚI BẾN (ĐƠN GIẢN – CHẮC ĂN) =========
    arrival_df = processed_df.join(stops_df) \
        .withColumn(
            "distance_m",
            haversine_udf(
                col("lat"), col("lon"),
                col("stop_lat"), col("stop_lon")
            )
        ).filter(
            col("distance_m") < 80   # 👉 CHỈ DÙNG KHOẢNG CÁCH
        ).select(
            "bus_id",
            "stop_id",
            current_timestamp().alias("arrived_at"),
            "distance_m"
        )

    if not arrival_df.isEmpty():
        arrival_df.write.jdbc(
            url=JDBC_URL,
            table="bus_stop_events",
            mode="append",
            properties=DB_PROPERTIES
        )
        print(f"🚌 Arrival events: {arrival_df.count()}")

    processed_df.unpersist()


# ========= 6. START STREAM =========
query = (
    stream_df.writeStream
    .foreachBatch(process_batch)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .start()
)

query.awaitTermination()
