import os 
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(redis_url)
