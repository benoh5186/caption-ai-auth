from services.subtitle_styler import SubtitleStyler
from services.client_connector import ClientUtility
from urllib.parse import quote
from services.subtitle_embedder import SubtitleEmbedder
import os 
import tempfile
from pymongo import MongoClient
import datetime 
import subprocess
import json 


def render_vid_job(job_id: str, session_id: str, user_id: str, bucket_name: str, burned_video_bucket: str):
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
        transcript = session_mongodb.get("transcript")
        style_data = session_mongodb.get("session_info")
        if s3_key is None or transcript is None or style_data is None:
            __set_job_failed("missing data to render caption", mongo_jobs_coll, job_id, user_id)
            return
        video_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={'Bucket' : bucket_name, 'Key' : s3_key},
            ExpiresIn=3600
        )
        with tempfile.NamedTemporaryFile(delete=True, suffix=".mp4") as output_path:
            render_request = {
                                "inputProps": 
                                    {"transcript": transcript, "segmentStyles": style_data, "videoSrc": video_url},
                                "outputLocation":
                                    output_path.name
                                }

            subprocess.run(
                ["npx", "tsx", "renderers/remotion/src/render.ts"],
                input=json.dumps(render_request),
                text=True,
                check=True
            )
            result_s3_key = f"exports/{user_id}/{session_id}/{job_id}.mp4"
            s3_client.upload_file(
                output_path.name,
                burned_video_bucket,
                result_s3_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
            mongo_jobs_coll.update_one(
                {"job_id" : job_id,
                 "user_id" : user_id
                 },
                 {
                     "$set" : {
                         "completed" : True, 
                         "finished_at" : datetime.datetime.utcnow(),
                         "result_s3_key" : result_s3_key
                     }
                 }
            )

    except Exception as exc:
        print(f"FAILED: {exc}")
        if mongo_jobs_coll is not None:
            __set_job_failed(str(exc), mongo_jobs_coll, job_id, user_id)
        else:
            print("render job failed before the job collection was available") 
    


def render_video_job(job_id: str, session_id: str, user_id: str, bucket_name: str, burned_video_bucket: str):
    temp_subtitle_path = None 
    temp_video_path = None 
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
        transcript = session_mongodb.get("transcript")
        style_data = session_mongodb.get("session_info")
        if s3_key is None or transcript is None or style_data is None:
            __set_job_failed("missing data to render caption", mongo_jobs_coll, job_id, user_id)
            return
        temp_video_path, temp_subtitle_path = __create_subtitle_and_video_files(s3_client, s3_key, bucket_name, transcript, style_data)
        subtitle_embedder = SubtitleEmbedder(temp_video_path, temp_subtitle_path)
        with tempfile.NamedTemporaryFile(delete=True) as output_path:
            with open(output_path.name, "wb") as f:
                for chunk in subtitle_embedder.embed_streaming():
                    f.write(chunk)
            result_s3_key = f"exports/{user_id}/{session_id}/{job_id}.mp4"
            s3_client.upload_file(
                output_path.name,
                burned_video_bucket,
                result_s3_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
            mongo_jobs_coll.update_one(
                {"job_id" : job_id,
                 "user_id" : user_id
                 },
                 {
                     "$set" : {
                         "completed" : True, 
                         "finished_at" : datetime.datetime.utcnow(),
                         "result_s3_key" : result_s3_key
                     }
                 }
            )
    except Exception as exc:
        if mongo_jobs_coll is not None:
            __set_job_failed(str(exc), mongo_jobs_coll, job_id, user_id)
        else:
            print("render job failed before the job collection was available")

    finally:
        if temp_subtitle_path and os.path.exists(temp_subtitle_path):
            os.unlink(temp_subtitle_path)
        if temp_video_path and os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
    

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
        

def __create_subtitle_and_video_files(s3_client, s3_key, bucket_name, transcript, style_data):
    suffix = os.path.splitext(s3_key)[1] or ".mp4"
    temp_video_path = None
    temp_subtitle_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as video_file:
            temp_video_path = video_file.name
            s3_client.download_fileobj(bucket_name, s3_key, video_file)
        with tempfile.NamedTemporaryFile(delete=False) as subtitle_file:
            temp_subtitle_path = subtitle_file.name
            subtitle_styler = SubtitleStyler(transcript)
            subtitle_styler.implement_styling(style_data, temp_subtitle_path)
        return video_file.name, subtitle_file.name
    except Exception:
        if temp_subtitle_path and os.path.exists(temp_subtitle_path):
            os.unlink(temp_subtitle_path)
        if temp_video_path and os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
