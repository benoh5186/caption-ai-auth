from fastapi import APIRouter, HTTPException, Request
from auth import AuthUtility
from db.db import Database
from motor.motor_asyncio import AsyncIOMotorClient

class SessionRouter:
    def __init__(self, user_sessions: Database, mongo_db: AsyncIOMotorClient,auth_utility: AuthUtility):
        self.__router = APIRouter(prefix="/session", tags=["session"])
        self.__user = user_sessions
        self.__auth_utility = auth_utility
        self.__user_session_metadata = mongo_db["user_session_metadata"]

    async def load_sessions(self):
        pass

    async def load_session(self):
        pass
    async def create_session(self):
        pass
    async def delete_session(self):
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
            "session_info": session_info,
        }
        result = await self.__user_session_metadata.update_one(
            {"user_id": session_payload.get("sub")},
            {"$set":insert_payload})
        return {
            "message": "Session saved successfully.",
            "session_id": str(result.inserted_id),
        }

        
        