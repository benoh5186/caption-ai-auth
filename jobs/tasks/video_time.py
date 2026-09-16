from services.client_connector import ClientUtility
from pymongo import MongoClient
from datetime import datetime
import subprocess
import os 


def video_time_job(job_id: str, session_id: str, user_id: str, bucket_name: str):
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