from jobs.redis_conn import redis_conn
from rq import Worker, SimpleWorker

worker = SimpleWorker(['default'], connection=redis_conn)
worker.work()