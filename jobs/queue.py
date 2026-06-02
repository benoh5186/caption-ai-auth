import os 
import redis
from rq import Queue 


redis_url = os.getenv("REDIS_URL")



redis_queue = Queue('default', connection=redis_url)