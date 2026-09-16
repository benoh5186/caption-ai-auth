from services.client_connector import ClientUtility
from pymongo import MongoClient
import datetime
import tempfile 
import subprocess
import os 
from datetime import datetime

def thumbnail_job(job_id, session_id, user_id, bucket_name, timestamp: str = "00:00:01"):
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
        thumbnail_s3_key = f"thumbnails/{session_id}.jpg"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as thumb_file:
            thumbnail_path = thumb_file.name
        subprocess.run(
                    [
                        "ffmpeg",
                        "-ss",
                        timestamp,
                        "-i",
                        video_url,
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=320:-1",
                        thumbnail_path,
                        "-y",
                    ],
                    check=True,
                    text=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
        with open(thumbnail_path, "rb") as file:
            thumbnail_bytes = file.read()
            s3_client.put_object(
                Bucket=bucket_name,  
                Key=thumbnail_s3_key,
                Body=thumbnail_bytes,
                ContentType="image/jpeg",
            )

        mongo_session_coll.update_one(
            {
                "user_id" : user_id,
                "session_id" : session_id
            }, {
                "$set" : {
                    "thumbnail_s3_key" : thumbnail_s3_key
                }    
                }
        )
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
    
    finally:
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

def __set_job_failed(reason: str, mongo_jobs_coll, job_id: str, user_id: str):
    mongo_jobs_coll.update_one({
        "job_id" : job_id,
        "user_id" : user_id
    },
    {
        "$set" : {
            "error" : reason,
            "completed" : False,
            "finished_at" : datetime.datetime.utcnow()
        }
    }
    )