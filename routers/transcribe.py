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




class TranscribeRouter:
    def __init__(self, mongo_db: AsyncIOMotorClient, auth_utility: AuthUtility) -> None:
        self.__router = APIRouter(prefix="/transcribe", tags=["transcribe"])
        self.__bucket_name = os.getenv("S3_BUCKET")
        self.__burned_video = os.getenv("S3_BURNED_VIDEO")
        self.__transcribe_endpoint = "https://dummy.api/transcribe"  # Dummy endpoint for now.
        self.__download_endpoint = "https://dummy.api/download"
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
            "/transcribe",
            self.transcribe,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/download/{video_id}",
            self.download,
            methods=["GET"],
        )
        self.__router.add_api_route(
            "/save-session",
            self.save_session,
            methods=["POST"],
        )

    async def download(self, video_id: str, request: Request):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=1,
            window_seconds=30,
            route_name="/download",
        )
        session_payload = self.__auth_utility.require_session(request)

        session_mongodb = await self.__user_session_metadata.find_one(
            {
                "user_id": session_payload.get("sub"),
                "video_id": video_id,
            }
        )
        if not session_mongodb:
            raise HTTPException(status_code=404, detail="Video metadata not found.")

        session_metadata = session_mongodb.get("session_info", {})
        s3_key = session_mongodb.get("s3_key")
        if not s3_key:
            raise HTTPException(status_code=404, detail="Video storage key not found.")

        payload = {
            "video_id": session_mongodb.get("video_id"),
            "s3_key": session_mongodb.get("s3_key"),
            "s3_burned_video_bucket": self.__burned_video,
            "video_metadata": session_metadata,
            "transcript" : session_mongodb.get("transcript")
        }
        try: 
            async with httpx.AsyncClient() as client:
                response = await client.post(self.__download_endpoint, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Download endpoint returned an error: {exc.response.status_code}",
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse download endpoint response: {exc}",
            ) from exc
        
        try:
            s3_object = self.__s3_client.get_object(
                Bucket=self.__burned_video,
                Key=s3_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 download failed: {exc}") from exc

        content_type = s3_object.get("ContentType") or "video/mp4"
        filename = quote(os.path.basename(s3_key))
        return StreamingResponse(
            self.__iter_video(s3_object["Body"]),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


    async def transcribe(self, request: Request, video: UploadFile = File(...), metadata: str = Form(...)):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=2,
            window_seconds=60,
            route_name="/transcribe",
        )
        payload = self.__auth_utility.require_session(request)
        if not self.__bucket_name:
            raise HTTPException(status_code=500, detail="S3_BUCKET is not configured.")

        content_type = video.headers.get("content-type", "")
        if not content_type.startswith("video/"):
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Expected video/* content type.",
            )

        video_bytes = await video.read()
        if not video_bytes:
            raise HTTPException(status_code=400, detail="Request body is empty.")

        # Will need to put this video id into nosql data collection 
        video_id = str(uuid.uuid4())
        try: 
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata must be valid JSON")
        if not isinstance(metadata_dict, dict):
            raise HTTPException(status_code=400, detail="metadata must be JSON object")
        session_id = metadata_dict.get("session_id")
        if not session_id or not isinstance(session_id, str):
            raise HTTPException(status_code=400, detail="session_id is required.")
        extension = self.__extension_from_content_type(content_type)
        if extension == "bin":
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Could not determine a valid video format.",
            )
        s3_key = f"videos/{video_id}.{extension}"

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
        
        session_doc = await self.__user_session_metadata.find_one(
         {"user_id": session_payload.get("sub"), "session_id": session_id}
         )
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found.")
        
        await self.__user_session_metadata.update_one(
            {"user_id" : payload.get("sub"),
             "session_id" : session_id},
            {"$set" : {
                "video_id": video_id,
                "s3_key": s3_key,}
              }   
        )

        session_payload = {
            "video_id": video_id,
            "bucket": self.__bucket_name,
            "s3_key": s3_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.__transcribe_endpoint, json=session_payload)
                response.raise_for_status()
                transcript = response.json()
                await self.__user_session_metadata.update_one(
                    {"user_id" : payload["sub"],
                     "session_id" : session_id
                     },
                    {"$set": {"transcript": transcript}}
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
    
    @staticmethod
    def __iter_video(streaming_body, chunk_size: int = 1024 * 1024):
        while chunk := streaming_body.read(chunk_size):
            yield chunk
