from services.client_connector import ClientUtility
from pymongo import MongoClient
import datetime
import tempfile 
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
            thumbnail_s3_key = __create_vid_thumbnail(session_id, temp_vid.name, s3_client, bucket_name)
            mongo_session_coll.update_one(
                {
                    "user_id" : user_id,
                    "session_id" : session_id
                }, {
                    "$set" : {
                        "vid_time" : float(result.stdout.strip()),
                        "upload_status" : "complete",
                        "thumbnail_s3_key" : thumbnail_s3_key
                    }      
                })

    except Exception as exc:
        __set_job_failed(str(exc), mongo_jobs_coll, job_id, user_id)

def __create_vid_thumbnail(session_id, video_path, s3_client, bucket_name, timestamp: str = "00:00:01"):
    thumbnail_s3_key = f"thumbnails/{session_id}.jpg"
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as thumb_file:
        thumbnail_path = thumb_file.name
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss",
                timestamp,
                "-i",
                video_path,
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
        return thumbnail_s3_key
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