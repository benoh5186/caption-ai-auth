from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from auth import AuthUtility
from db.db import Database
from motor.motor_asyncio import AsyncIOMotorClient
import os 
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.responses import StreamingResponse, JSONResponse
from urllib.parse import quote
import uuid

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

    def __register_routes(self):
        self.__router.add_api_route(
            "/load-sessions",
            self.load_sessions,
            methods=["GET"]
        )
        self.__router.add_api_route(
            "/load-session/{session_id}",
            self.load_session,
            methods=["GET"]
        )
        self.__router.add_api_route(
            "load-session-video/{session_id}",
            self.load_session_video,
            methods=["POST"]
        )
        self.__router.add_api_route(
            "create-session",
            self.create_session,
            methods=["GET"]
        )
        self.__router.add_api_route(
            "delete-session/{session_id}",
            self.delete_session,
            methods=["DELETE"]
        )
        self.__router.add_api_route(
            "save-session",
            self.save_session,
            methods=["POST"]
        )

    async def load_sessions(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=30,
            route_name="/load-sessions",
        )
        session_payload = self.__auth_utility.require_session(request)
        cursor = self.__user_session_metadata.find(
            {"user_id" : session_payload.get("sub")},
            {"_id": 0, "session_id": 1},
            )
        sessions = await cursor.to_list(length=100)
        return sessions 


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
            },
            {"_id": 0},
        )

    async def upload_video(self, request: Request, video: UploadFile = File(...)):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=30,
            route_name="/load-session-video",
        )
        session_payload = self.__auth_utility.require_session(request)
        session_id = request.query_params.get("session_id")
        content_type = video.headers.get("content-type", "")
        
        if not self.__bucket_name:
            raise HTTPException(status_code=500, detail="S3_BUCKET is not configured.")
              
        if not content_type.startswith("video/"):
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Expected video/* content type.",
            )
        video_bytes = await video.read()
        if not video_bytes:
            raise HTTPException(status_code=400, detail="Request body is empty.")
        video_id = str(uuid.uuid4())
        extension = self.__extension_from_content_type(content_type)
        s3_key = f"videos/{video_id}.{extension}"
        session_doc = await self.__user_session_metadata.find_one(
         {"user_id": session_payload.get("sub"), "session_id": session_id}
         )
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found.")
        
        try:
            self.__s3_client.put_object(
                Bucket=self.__bucket_name,
                Key=s3_key,
                Body=video_bytes,
                ContentType=content_type,
                Metadata={
                    "video_id": video_id,
                    "session_id" : session_id
                          },
            )

        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc
        await self.__user_session_metadata.update_one(
            {"user_id" : session_payload["sub"],
             "session_id" : session_id
             },
            {"$set": {
                "video_id": video_id,
                "s3_key": s3_key}}
            )
        
        return {"s3_key" : s3_key}
        


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
        except self.__s3_client.exceptions.NoSuchKey as exc:
            raise HTTPException(status_code=404, detail="Video not found")
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 download failed: {exc}") from exc
        filename = quote(os.path.basename(s3_key))
        return StreamingResponse(
            self.__iter_video(s3_object["Body"]),
            media_type="video/mp4",
            headers={"Content-Disposition": f'inline; filename={filename}'},
        )       

    async def create_session(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=5,
            route_name="/create-session",
        )
        session_payload = self.__auth_utility.require_session(request)
        session_id = str(uuid.uuid4())
        try:
            self.__user.increase_sessions_creation_count(session_payload["sub"])
            self.__user_session_metadata.insert_one({
                "user_id" : session_payload.get("sub"),
                "session_id" : session_id,
                "transcript" : None,
                "session_info" : None
            })
            return JSONResponse(
            status_code=201,
            content={ "session_id" : session_id},
            )
        except:
            raise HTTPException(status_code=403, detail="can't create anymore sessions")

    
    async def delete_session(self, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=5,
            route_name="/delete-session",
        )
        session_payload = self.__auth_utility.require_session(request)
        session_id = request.query_params.get("session_id")
        await self.__user_session_metadata.delete_one({
            "user_id" : session_payload.get("sub"),
            "session_id" : session_id
        })
        self.__user.decrease_sessions_creation_count(session_payload.get("sub"))
        return JSONResponse(
            status_code=201,
            content={"message" : "session deletion successful"}
        )


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
            {"$set": insert_payload})
        return {
            "message": "Session saved successfully."
        }
    
    @staticmethod
    def __iter_video(streaming_body, chunk_size: int = 1024 * 1024):
        while chunk := streaming_body.read(chunk_size):
            yield chunk

    @staticmethod
    def __extension_from_content_type(content_type: str) -> str:
        subtype = content_type.split("/", 1)[1]
        clean_subtype = subtype.split(";", 1)[0].strip().lower()
        if clean_subtype in {"quicktime"}:
            return "mov"
        return clean_subtype or "bin"

    @property
    def router(self) -> APIRouter:
        return self.__router

        
        