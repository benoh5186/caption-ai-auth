from fastapi import APIRouter, HTTPException, Request
from auth import AuthUtility
from db.db import Database
from motor.motor_asyncio import AsyncIOMotorClient
import os 
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.responses import StreamingResponse
from urllib.parse import quote

class SessionRouter:
    def __init__(self, user_sessions: Database, mongo_db: AsyncIOMotorClient,auth_utility: AuthUtility):
        self.__router = APIRouter(prefix="/session", tags=["session"])
        self.__user = user_sessions
        self.__auth_utility = auth_utility
        self.__user_session_metadata = mongo_db["user_session_metadata"]
        self.__bucket_name = os.getenv("S3_BUCKET")
        self.__s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )

    async def load_sessions(self, request: Request):
        pass

    async def load_session(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=30,
            route_name="/load-session",
        )
        session_payload = self.__auth_utility.require_session(request)
        return await self.__user_session_metadata.find_one(
            {
                "user_id": session_payload.get("sub"),
                "session_id": request.query_params.get("session_id")
            }
        )
    async def load_session_video(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=30,
            route_name="/load-session-video",
        )
        self.__auth_utility.require_session(request)
        s3_key = request.query_params.get("s3_key")
        try:
            s3_object = self.__s3_client.get_object(
                Bucket=self.__bucket_name,
                Key=s3_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 download failed: {exc}") from exc
        filename = quote(os.path.basename(s3_key))
        return StreamingResponse(
            self.__iter_video(s3_object["Body"]),
            media_type="video/mp4",
            headers={"Content-Disposition": f'inline; filename={filename}'},
        )       




    async def create_session(self, request: Request):
        pass
    async def delete_session(self, request: Request):
        pass

    async def save_session(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=30,
            route_name="/save-session",
        )
        session_payload = self.__auth_utility.require_session(request)
        try:
            session_info = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

        if not isinstance(session_info, dict):
            raise HTTPException(status_code=400, detail="session_info must be a JSON object.")

        insert_payload = {
            "session_info": session_info["video_metadata"],
        }
        await self.__user_session_metadata.update_one(
            {"user_id": session_payload.get("sub"),
             "session_id": session_info["session_id"]},
            {"$set":insert_payload})
        return {
            "message": "Session saved successfully."
        }
    
    @staticmethod
    def __iter_video(streaming_body, chunk_size: int = 1024 * 1024):
        while chunk := streaming_body.read(chunk_size):
            yield chunk

        
        