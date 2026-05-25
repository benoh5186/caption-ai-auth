import os
import uuid
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from routers.auth import AuthUtility
from fastapi.responses import StreamingResponse
import json
from services.subtitle_styler import SubtitleStyler
from services.subtitle_embedder import SubtitleEmbedder
import tempfile 



class TranscribeRouter:
    def __init__(self, mongo_db: AsyncIOMotorClient, auth_utility: AuthUtility) -> None:
        self.__router = APIRouter(prefix="/api/v1/transcribe", tags=["transcribe"])
        self.__bucket_name = os.getenv("S3_BUCKET")
        self.__transcribe_endpoint = "http://localhost:9000/api/v1/transcribe-video"  
        self.__download_endpoint = "http://localhost:9000/api/v1/download-video"
        self.__s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
        self.__register_routes()
        self.__user_session_metadata = mongo_db["user_session_metadata"]
        self.__auth_utility = auth_utility

    def __register_routes(self) -> None:
        self.__router.add_api_route(
            "/transcribe/{session_id}",
            self.transcribe,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/download/{session_id}",
            self.download,
            methods=["POST"],
        )

    async def download(self, request: Request, session_id):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=60,
            route_name="/download",
        )
        session_payload = self.__auth_utility.require_session(request)
        session_mongodb = await self.__user_session_metadata.find_one(
            {
                "user_id": session_payload.get("sub"),
                "session_id": session_id 
            }
        )
        s3_key = session_mongodb.get("s3_key")
        s3_client = self.__get_s3_client()
        suffix = os.path.splitext(s3_key)[1] or ".mp4"
        temp_video_path = None
        temp_subtitle_path = None 
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as video_file:
                temp_video_path = video_file.name 
                s3_client.download_fileobj(self.__bucket_name, s3_key, video_file)
            with tempfile.NamedTemporaryFile(delete=False) as subtitle_file:
                temp_subtitle_path = subtitle_file.name 
                subtitle_styler = SubtitleStyler(session_mongodb.get("transcript"))
                subtitle_styler.implement_styling(session_mongodb.get("session_info"), temp_subtitle_path)
        except Exception as exc:
            print(exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        try:
            s3_object = self.__s3_client.get_object(
                Bucket=self.__bucket_name,
                Key=s3_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 download failed: {exc}") from exc
        
        subtitle_embedder = SubtitleEmbedder(temp_video_path, temp_subtitle_path)
        content_type = s3_object.get("ContentType") or "video/mp4"
        filename = quote(os.path.basename(s3_key))
        
        try:
            return StreamingResponse(
                content=subtitle_embedder.embed_streaming(),
                media_type=content_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
        except Exception as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        


    async def transcribe(self, request: Request, session_id):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=2,
            window_seconds=60,
            route_name="/transcribe",
        )
        payload = self.__auth_utility.require_session(request)
        if not self.__bucket_name:
            raise HTTPException(status_code=500, detail="S3_BUCKET is not configured.")
        
        session_mongodb = await self.__user_session_metadata.find_one(
            {
                "user_id": payload.get("sub"),
                "session_id": session_id,
            }
        )
        if not session_mongodb:
            raise HTTPException(status_code=404, detail="Session metadata not found.")
        if not session_mongodb.get("video_id") or not session_mongodb.get("s3_key"):
            raise HTTPException(status_code=404, detail="Video metadata not found.")
               
        session_payload = {
            "video_id": session_mongodb.get("video_id"),
            "bucket": self.__bucket_name,
            "s3_key": session_mongodb.get("s3_key"),
        }

        try:
            timeout = httpx.Timeout(300.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.__transcribe_endpoint, json=session_payload)
                print("transcribe status:", response.status_code)
                print("transcribe body:", response.text[:1000])
                response.raise_for_status()
                transcript = response.json()
                await self.__user_session_metadata.update_one(
                    {"user_id" : payload["sub"],
                     "session_id" : session_id
                     },
                    {"$set": {
                        "transcript": transcript}}
                )
            return transcript
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Transcribe endpoint returned an error: {exc.response.status_code}",
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse transcribe endpoint response: {exc}",
            ) from exc

    @property
    def router(self) -> APIRouter:
        return self.__router
    
    @staticmethod
    def __iter_video(streaming_body, chunk_size: int = 1024 * 1024):
        while chunk := streaming_body.read(chunk_size):
            yield chunk

    @staticmethod
    def __get_s3_client():
        aws_access_key = os.getenv("AWS_S3_ACCESS_KEY")
        aws_secret_key = os.getenv("AWS_S3_SECRET_KEY")
        aws_region = os.getenv("AWS_REGION")
        return boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
