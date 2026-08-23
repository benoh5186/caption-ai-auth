from services.client_connector import ClientUtility
from jobs.modal.transcribe_worker import TranscriptMaker
import datetime
from pymongo import MongoClient
import modal 
from datetime import datetime, timedelta, timezone

def transcribe_job(job_id: str, session_id: str, user_id: str, bucket_name: str):
    mongo_db = None 
    mongo_jobs_coll = None 
    try:
        user_db = ClientUtility.get_database()
        transcribe_info = __get_user_metadata(user_db, user_id)

        transcribable_time = transcribe_info.get("transcribable_time")
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
        vid_time = user_session.get("vid_time")


        if vid_time > transcribable_time:
            __set_job_failed("video time exceeds total transcribeable minutes user has left", mongo_jobs_coll, job_id, user_id)
            return 
        model = modal.Cls.from_name("transcriber", "TranscriptMaker")
        transcript = model().get_transcript.remote(bucket=bucket_name, s3_key=s3_key)
        if isinstance(transcript, str):
            __set_job_failed("failed to transcribe", mongo_jobs_coll, job_id, user_id) 
        mongo_session_coll.update_one({
            "user_id" : user_id,
            "session_id" : session_id
        }, {
            "$set" : {
                "transcript" : transcript
            }
        })
        updated_transcribable_time = transcribable_time - vid_time
        user_db.update_user_profile(user_id=user_id, metadata={"transcribe_info" : {
                        "transcribable_time" : updated_transcribable_time,
                        "last_updated" : transcribe_info.get("last_updated")
                    }})
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

def __get_user_metadata(user_db, user_id):
    refill_time = 3000
    user = user_db.get_user_by_id(user_id)
    transcribe_info = user.get("transcribe_info")
    now = datetime.now(tz=timezone.utc)
    elapsed = now - transcribe_info.get("last_updated")
    if elapsed >= timedelta(days=1):
        updated_metadata = {
             "transcribe_info" : {
                        "transcribable_time" : refill_time,
                        "last_updated" : now }
        }
        user_db.update_user_profile(user_id=user_id, metadata=updated_metadata) 
        return updated_metadata.get("transcribe_info")
    return transcribe_info


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