import os 
from redis import Redis

redis_url = os.getenv("REDIS_URL")
redis_conn = Redis(Redis.from_url(redis_url))
