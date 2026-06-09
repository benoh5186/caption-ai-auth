import os
import uuid
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from routers.auth import AuthUtility
from fastapi.responses import StreamingResponse
import json
from services.subtitle_styler import SubtitleStyler
from services.subtitle_embedder import SubtitleEmbedder
import tempfile 
from jobs.queue import enqueue_render_job
from redis import RedisError 
import datetime
from services.client_connector import ClientUtility


class TranscribeRouter:
    def __init__(self, mongo_db: AsyncIOMotorClient, auth_utility: AuthUtility) -> None:
        self.__router = APIRouter(prefix="/api/v1/transcribe", tags=["transcribe"])
        self.__bucket_name = os.getenv("S3_BUCKET")
        self.__burned_bucket_name = os.getenv("S3_BURNED_VIDEO")
        self.__transcribe_endpoint = "http://localhost:9000/api/v1/transcribe-video"  
        self.__register_routes()
        self.__user_session_metadata = mongo_db["user_session_metadata"]
        self.__job_info_metadata = mongo_db["background_jobs_collection"]
        self.__auth_utility = auth_utility

    def __register_routes(self) -> None:
        self.__router.add_api_route(
            "/transcribe/{session_id}",
            self.transcribe,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/export/{session_id}",
            self.export,
            methods=["POST"]
        )
        self.__router.add_api_route(
            "/export-status/{job_id}",
            self.export_status,
            methods=["GET"]
        )
        self.__router.add_api_route(
            "/download/{job_id}",
            self.download,
            methods=["POST"],
        )
        self.__router.add_api_route(
            "/transcript/{job_id}",
            self.transcript,
            methods=["POST"]
        )

    async def export(self, request: Request, session_id):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=60,
            route_name="/export",
        )
        session_payload = self.__auth_utility.require_session(request)
        job_id = str(uuid.uuid4())
        user_id = session_payload.get("sub")
        await self.__job_info_metadata.insert_one({
            "job_id" : job_id,
            "user_id" : user_id,
            "created_at" : datetime.datetime.utcnow(),
            "completed" : None,
            "error" : None 
        })
        try:
            enqueue_render_job(
                job_id=job_id, 
                session_id=session_id, 
                user_id=user_id, 
                bucket_name=self.__bucket_name, 
                burned_video_bucket=self.__burned_bucket_name
            )
        except RedisError:
            await self.__job_info_metadata.delete_one({
                "job_id": job_id,
                "user_id": user_id,
            })
            raise HTTPException(status_code=503, detail="redis queue is unavailable")
        except Exception:
            await self.__job_info_metadata.delete_one({
                "job_id": job_id,
                "user_id": user_id,
            })
            raise HTTPException(status_code=500, detail="failed to enqueue render job.")
        return {"job_id" : job_id}

    async def export_status(self, request: Request, job_id: str):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=60,
            route_name="/export-status",
        )
        session_payload = self.__auth_utility.require_session(request)
        job = await self.__job_info_metadata.find_one(
            {"job_id" : job_id,
             "user_id" : session_payload.get("sub")
             }
        )
        if job is None:
            print("not found")
            raise HTTPException(status_code=404)
        status = job["completed"]
        if status is not None:
            return  {
                "completed" : status,
                "error" : job.get("error", None) 
            }
        else:
            return {
                "completed" : None,
                "error" : None 
            }
        
    async def download(self, request: Request, job_id):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=10,
            window_seconds=60,
            route_name="/download",
        )
        session_payload = self.__auth_utility.require_session(request)
        export_job = await self.__job_info_metadata.find_one(
            {"job_id" : job_id,
             "user_id" : session_payload.get("sub")
             })
        if export_job is None:
            raise HTTPException(status_code=404)
        
        burned_video_s3 = export_job.get("result_s3_key")
        if not burned_video_s3:
            raise HTTPException(status_code=500)
        s3_client = ClientUtility.get_s3_client()

        s3_object = s3_client.get_object(Bucket=self.__burned_bucket_name, Key=burned_video_s3)

        filename = quote(os.path.basename(burned_video_s3))

        return StreamingResponse(
            self.__iter_video(s3_object["Body"]),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        
        )
        


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

        job_id = str(uuid.uuid4())
        user_id = session_payload.get("sub")
        await self.__job_info_metadata.insert_one({
            "job_id" : job_id,
            "user_id" : user_id,
            "created_at" : datetime.datetime.utcnow(),
            "completed" : None,
            "error" : None 
        })

        if not session_mongodb:
            raise HTTPException(status_code=404, detail="Session metadata not found.")
        if not session_mongodb.get("s3_key"):
            raise HTTPException(status_code=404, detail="Video metadata not found.")
               
        session_payload = {
            "bucket": self.__bucket_name,
            "s3_key": session_mongodb.get("s3_key"),
            "user_id" : user_id,
            "job_id" : job_id,
            "session_id" : session_id
        }

        try:
            timeout = httpx.Timeout(300.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.__transcribe_endpoint, json=session_payload)
                print("transcribe status:", response.status_code)
                print("transcribe body:", response.text[:1000])
                response.raise_for_status()
            return {"job_id" : job_id}
        except httpx.HTTPStatusError as exc:
            print(exc.response.status_code)
            print(exc.response.content)
            raise HTTPException(
                status_code=502,
                detail=f"failed to enqueue job.",
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse transcribe endpoint response: {exc}",
            ) from exc
        
    async def transcript(self, request: Request, session_id):
        self.__auth_utility.enforce_rate_limit(
            request=request,
            max_requests=2,
            window_seconds=60,
            route_name="/transcript",
        )
        session_payload = self.__auth_utility.require_session(request)
        session_doc = await self.__user_session_metadata.find_one(
            {"user_id" : session_payload.get("sub"), 
             "session_id" : session_id})
        transcript = session_doc["transcript"]
        if transcript is None:
            return HTTPException(status_code=404)
        return transcript 

    @property
    def router(self) -> APIRouter:
        return self.__router
    
    @staticmethod
    def __iter_video(streaming_body, chunk_size: int = 1024 * 1024):
        while chunk := streaming_body.read(chunk_size):
            yield chunk
