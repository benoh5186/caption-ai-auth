from services.client_connector import ClientUtility
from jobs.modal.transcribe_worker import TranscriptMaker
import datetime
from pymongo import MongoClient

def transcribe_job(job_id: str, session_id: str, user_id: str, bucket_name: str):
    mongo_db = None 
    mongo_jobs_coll = None 
    try:
        mongo_client: MongoClient = ClientUtility.get_mongo_client()
        mongo_db = mongo_client["caption_ai"]
        mongo_session_coll = mongo_db["user_session_metadata"]
        mongo_jobs_coll = mongo_db["background_jobs_collection"]
        user_session = mongo_session_coll.find_one({
            "user_id" : user_id,
            "session_id" : session_id
        })
        if user_session is None:
            __set_job_failed("session does not exist for this job", mongo_jobs_coll, job_id, user_id)
            return 
        s3_key = user_session.get("s3_key")
        transcript = TranscriptMaker().get_transcript(bucket_name, s3_key)
        if type(transcript) is str:
            __set_job_failed("failed to transcribe", mongo_jobs_coll, job_id, user_id) 
        mongo_session_coll.update_one({
            "user_id" : user_id,
            "session_id" : session_id
        }, {
            "$set" : {
                "transcript" : transcript
            }
        })
        mongo_jobs_coll.update_one({
            "user_id" : user_id,
            "session_id" : session_id 
        }, { 
            "$set" : {
                "completed" : True,
                "finished_at" : datetime.datetime.utcnow()
            }
        })



    except Exception as exc:
        print(f"FAILED: {exc}")
        if mongo_jobs_coll is not None:
            __set_job_failed(str(exc), mongo_jobs_coll, job_id, user_id)
        else:
            print("render job failed before the job collection was available")  


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