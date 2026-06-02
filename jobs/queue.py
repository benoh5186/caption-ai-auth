import os 
from rq import Queue
from redis import Redis


redis_url = os.getenv("REDIS_URL")
redis_conn = Redis(redis_url)


redis_queue = Queue('default', connection=redis_conn)

def enqueue_render_job():
    pass