import os
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request


class TranscribeRouter:
    def __init__(self) -> None:
        self.__router = APIRouter(prefix="/transcribe", tags=["transcribe"])
        self.__bucket_name = os.getenv("S3_BUCKET")
        self.__s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
        self.__register_routes()

    def __register_routes(self) -> None:
        self.__router.add_api_route(
            "/transcribe",
            self.transcribe,
            methods=["POST"],
        )

    async def transcribe(self, request: Request):
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

        return {
            "video_id": video_id,
            "bucket": self.__bucket_name,
            "s3_key": s3_key,
            "message": "Video uploaded successfully.",
        }

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
