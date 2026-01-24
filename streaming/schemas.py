"""
schemas.py
-----------
Định nghĩa schema cho dữ liệu GPS gửi từ Kafka
"""

from pyspark.sql.types import StructType, StringType, DoubleType


def get_gps_schema():
    return StructType() \
        .add("bus_id", StringType()) \
        .add("route_id", StringType()) \
        .add("lat", DoubleType()) \
        .add("lon", DoubleType()) \
        .add("speed", DoubleType()) \
        .add("timestamp", StringType())
