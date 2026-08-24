from services.client_connector import ClientUtility
from pymongo import MongoClient
import datetime
import tempfile 
import subprocess


def video_time_job(job_id: str, session_id: str, user_id: str, bucket_name: str):
    mongo_db = None 
    mongo_jobs_coll = None
    try:
        user_db = ClientUtility.get_database()
        mongo_client: MongoClient = ClientUtility.get_mongo_client()
        mongo_db = mongo_client["caption_ai"]
        mongo_session_coll = mongo_db["user_session_metadata"]
        mongo_jobs_coll = mongo_db["background_jobs_collection"]
        s3_client = ClientUtility.get_s3_client() 
        session_mongodb = mongo_session_coll.find_one({
            "user_id" : user_id,
            "session_id" : session_id
        })
        if session_mongodb is None:
            __set_job_failed("session does not exist for this job", mongo_jobs_coll, job_id, user_id)
            return 
        s3_key = session_mongodb.get("s3_key")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_vid:
            s3_client.download_fileobj(
                Bucket=bucket_name,
                Key=s3_key,
                Fileobj=temp_vid
            )
            temp_vid.flush()
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    temp_vid.name,
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

    except Exception as exc:
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
            "finished_at" : datetime.datetime.utcnow()
        }
    }
    )