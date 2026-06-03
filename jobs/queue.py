import os 
from rq import Queue
from redis import Redis
from jobs.tasks.render import render_video_job
from jobs.redis_conn import redis_conn


redis_queue = Queue('default', connection=redis_conn)

def enqueue_render_job(job_id: str, session_id: str, user_id: str, bucket_name: str, burned_video_bucket: str):
    redis_queue.enqueue(
        render_video_job,
        kwargs={
            "job_id" : job_id,
            "session_id" : session_id,
            "user_id" : user_id,
            "bucket_name" : bucket_name,
            "burned_video_bucket" : burned_video_bucket
        }
    )
    