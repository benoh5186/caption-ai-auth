from jobs.queue import redis_conn
from rq import Worker

worker = Worker(['default'], redis_conn)
worker.work()