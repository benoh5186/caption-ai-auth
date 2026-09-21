from services.client_connector import ClientUtility
from pymongo import MongoClient
from datetime import datetime
import subprocess
import os 


def video_time_job(job_id: str, session_id: str, user_id: str, bucket_name: str):
    # vid time job must first check if given video is within disk space of given hosted hardware
    mongo_db = None 
    mongo_jobs_coll = None
    try:
        mongo_client: MongoClient = ClientUtility.get_mongo_client()
        mongo_db = mongo_client["caption_ai"]
        mongo_session_coll = mongo_db["user_session_metadata"]
        mongo_jobs_coll = mongo_db["background_jobs_collection"]
        s3_client = ClientUtility.get_s3_client() 
        session_mongodb = mongo_session_coll.find_one({
            "user_id" : user_id,
            "session_id" : session_id
        })
        print("starting vid time job!!")
        if session_mongodb is None:
            print("yea mongodb not available")
            __set_job_failed("session does not exist for this job", mongo_jobs_coll, job_id, user_id)
            return 
        s3_key = session_mongodb.get("s3_key")
        __check_vid_size(s3_client=s3_client, bucket=bucket_name, s3_key=s3_key)
        video_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name,
                "Key": s3_key 
            },
            ExpiresIn=900
        )
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_url,
            ],
            capture_output=True,
            text=True,
            check=True
        )
        mongo_session_coll.update_one(
            {
                "user_id" : user_id,
                "session_id" : session_id
            }, {
                "$set" : {
                    "vid_time" : float(result.stdout.strip()),
                    "upload_status" : "complete"
                }      
            })
        mongo_jobs_coll.update_one({
                    "user_id" : user_id,
                    "job_id" : job_id 
                }, { 
                    "$set" : {
                        "completed" : True,
                        "finished_at" : datetime.utcnow()
                    }
                })

    except Exception as exc:
        print(f"okie failed: {str(exc)}")
        __set_job_failed(str(exc), mongo_jobs_coll, job_id, user_id)
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=s3_key
        )


def __set_job_failed(reason: str, mongo_jobs_coll, job_id: str, user_id: str):
    mongo_jobs_coll.update_one({
        "job_id" : job_id,
        "user_id" : user_id
    },
    {
        "$set" : {
            "error" : reason,
            "completed" : False,
            "finished_at" : datetime.utcnow()
        }
    }
    )

def __check_vid_size(s3_client, bucket, s3_key):
    allowed_size = 250 * 1024 * 1024
    object_metadata = s3_client.head_object(
        Bucket=bucket,
        Key=s3_key 
    )
    content_length = object_metadata["ContentLength"]
    if content_length > allowed_size:
        raise ValueError("Video file is too large.")
