import os
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from routers.auth import AuthUtility




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

    async def download(self, request: Request):
        self.__auth_utility.enforce_rate_limit(max_requests=1, window_seconds=30, route_name="/download")
        payload = self.__auth_utility.require_session(request)
        try:
            session_info = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc
        if not isinstance(session_info, dict):
            raise HTTPException(status_code=400, detail="session_info must be a JSON object.")
        session_metadata = await self.__user_session_metadata.find_one({payload.get("sub")})
        


 

    async def save_session(self, request: Request):
        self.__auth_utility.enforce_rate_limit(max_requests=1, window_seconds=30, route_name="/save-session")
        session_payload = self.__auth_utility.require_session(request)
        try:
            session_info = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

        if not isinstance(session_info, dict):
            raise HTTPException(status_code=400, detail="session_info must be a JSON object.")

        insert_payload = {
            "user_id": session_payload.get("sub"),
            "email": session_payload.get("email"),
            "session_info": session_info,
        }
        result = await self.__user_session_metadata.insert_one(insert_payload)
        return {
            "message": "Session saved successfully.",
            "session_id": str(result.inserted_id),
        }




    async def transcribe(self, request: Request):
        self.__auth_utility.enforce_rate_limit(max_requests=2, window_seconds=60, route_name="/transcribe")
        payload = self.__auth_utility.require_session(request)
        if not self.__bucket_name:
            raise HTTPException(status_code=500, detail="S3_BUCKET is not configured.")

        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("video/"):
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Expected video/* content type.",
            )

        video_bytes = await request.body()
        if not video_bytes:
            raise HTTPException(status_code=400, detail="Request body is empty.")

        # Will need to put this video id into nosql data collection 
        video_id = str(uuid.uuid4())
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
                Metadata={"video_id": video_id},
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc
        
        self.__user_session_metadata.insert_one(
            {
                "user_id" : payload.get("sub"),
                "video_id" : video_id,
                "s3_key" : s3_key
            }
        )

        payload = {
            "video_id": video_id,
            "bucket": self.__bucket_name,
            "s3_key": s3_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.__transcribe_endpoint, json=payload)
                response.raise_for_status()
            return response.json()
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
