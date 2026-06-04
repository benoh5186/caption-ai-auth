from services.client_connector import ClientUtility
import datetime


def clean_up_expired_jobs():   
    mongo_client = ClientUtility.get_mongo_client()
    mongo_db = mongo_client["caption_ai"]
    mongo_jobs_coll = mongo_db["background_jobs_collection"]

    cut_off = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    
    mongo_jobs_coll.delete_many(
        {
            "completed": {"$in" : [True, False]},
            "finished_at": {"$lt" : cut_off }
        })

