import redis
import json

class RedisStore:
    def __init__(self, host="redis", port=6379):
        # Kết nối tới container redis trong mạng Docker
        self.client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )

    def save_location_batch(self, rows):
        """
        Ghi dữ liệu của tất cả các xe vào Redis trong một lượt (Pipeline)
        để đảm bảo hiệu suất streaming.
        """
        pipe = self.client.pipeline()
        for row in rows:
            bus_id = row["bus_id"]
            # Cập nhật vị trí và tốc độ xe
            pipe.set(
                f"bus:{bus_id}:location",
                json.dumps({
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "speed": row["speed"]
                })
            )
            # Cập nhật mốc thời gian mới nhất
            pipe.set(f"bus:{bus_id}:last_update", row["timestamp"])
        
        # Thực thi đồng loạt
        pipe.execute()