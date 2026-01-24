from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp
from schemas import get_gps_schema
from spark_reader import read_kafka_stream
from redis_store import RedisStore

# ========= 1. KHỞI TẠO SPARK SESSION =========
spark = (
    SparkSession.builder
    .appName("BusRealtimeStreaming")
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0")
    .config("spark.sql.streaming.checkpointLocation", "/app/checkpoints")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ========= 2. THÔNG TIN KẾT NỐI =========
JDBC_URL = "jdbc:postgresql://host.docker.internal:5432/bus_tracking_system"
DB_PROPERTIES = {
    "user": "postgres",
    "password": "Thienanh1906@",
    "driver": "org.postgresql.Driver"
}
KAFKA_SERVERS = "kafka:9093"
KAFKA_TOPIC = "bus_location"
CHECKPOINT_PATH = "/tmp/bus_tracking_checkpoint"


schema = get_gps_schema()
redis_store = RedisStore(host="redis") 
stream_df = read_kafka_stream(spark, KAFKA_SERVERS, KAFKA_TOPIC, schema)

# ========= 3. LOGIC XỬ LÝ CHÍNH =========
def process_batch(batch_df, batch_id):
    if batch_df.count() > 0:
        print(f"🚀 Processing Batch {batch_id} - {batch_df.count()} records")
        
        # A. Ép kiểu dữ liệu thời gian
        processed_df = batch_df.withColumn(
            "ts_casted", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        )
        
        # B. Ghi vào Redis
        rows = batch_df.collect()
        redis_store.save_location_batch(rows)
        
        # C. Ghi vào Postgres (Bảng Log)
        log_df = processed_df.select(
            col("bus_id"), col("lat"), col("lon"), col("speed"), 
            col("ts_casted").alias("ts")
        )
        log_df.write.jdbc(url=JDBC_URL, table="bus_gps_log", mode="append", properties=DB_PROPERTIES)
        
        # D. UPSERT vào Postgres (Bảng Current Status)
        status_df = processed_df.select(
            col("bus_id"), col("lat"), col("lon"), col("speed"), 
            col("ts_casted").alias("last_update")
        )
        # Ghi vào bảng tạm
        status_df.write.jdbc(url=JDBC_URL, table="temp_bus_status", mode="overwrite", properties=DB_PROPERTIES)
        
        # Thực thi UPSERT query
        upsert_query = """
            INSERT INTO bus_current_status (bus_id, lat, lon, speed, last_update)
            SELECT bus_id, lat, lon, speed, last_update FROM temp_bus_status
            ON CONFLICT (bus_id) 
            DO UPDATE SET 
                lat = EXCLUDED.lat, 
                lon = EXCLUDED.lon, 
                speed = EXCLUDED.speed, 
                last_update = EXCLUDED.last_update;
        """
        
        conn = None
        try:
            conn = spark._sc._gateway.jvm.java.sql.DriverManager.getConnection(JDBC_URL, DB_PROPERTIES["user"], DB_PROPERTIES["password"])
            stmt = conn.createStatement()
            stmt.execute(upsert_query)
            stmt.close()
            print(f"✅ Data synced successfully for Batch {batch_id}")
        except Exception as e:
            print(f"❌ Error during UPSERT: {e}")
        finally:
            if conn: conn.close()

# ========= 4. CHẠY LUỒNG =========
query = (
    stream_df.writeStream
    .foreachBatch(process_batch)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .start()
)
query.awaitTermination()