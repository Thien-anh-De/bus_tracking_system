from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType

def get_gps_schema():
    return (
        StructType()
        .add("bus_id", StringType())
        .add("lat", DoubleType())
        .add("lon", DoubleType())
        .add("speed", IntegerType())
        .add("direction", IntegerType())
        .add("timestamp", StringType())
    )
