import os
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv
from redis.asyncio import Redis  


load_dotenv()


class ClientUtility():
    @staticmethod
    def get_mongo_client():
        return MongoClient(os.getenv("MONGO_DB_CONNECTION"))

    @staticmethod
    def get_async_mongo_client():
        return AsyncIOMotorClient(os.getenv("MONGO_DB_CONNECTION"))

    @staticmethod
    def get_s3_client():
        return boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
    @staticmethod
    def get_async_redis_client():
        return Redis(os.getenv("REDIS_URL"))
