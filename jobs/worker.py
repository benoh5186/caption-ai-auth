from jobs.redis_conn import redis_conn
from rq import Worker

worker = Worker(['default'], connection=redis_conn)
worker.work()