import redis
import json

class RedisStore:
    def __init__(self, host="redis", port=6379):
        self.client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )

    def save_location_batch(self, rows):
        pipe = self.client.pipeline()

        for row in rows:
            r = row.asDict()

            bus_id = r["bus_id"]

            pipe.set(
                f"bus:{bus_id}:location",
                json.dumps({
                    "lat": r["lat"],
                    "lon": r["lon"],
                    "speed": r["speed"],
                    "direction": r.get("direction", 0)
                })
            )

            # ✅ DÙNG ts (ĐÃ CAST) – KHÔNG DÙNG timestamp
            pipe.set(
                f"bus:{bus_id}:last_update",
                r["ts"].strftime("%Y-%m-%d %H:%M:%S")
            )

        pipe.execute()
