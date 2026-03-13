from fastapi import APIRouter
from auth import AuthUtility
from db.db import Database
from motor.motor_asyncio import AsyncIOMotorClient

class SessionRouter:
    def __init__(self, user_sessions: Database, mongo_db: AsyncIOMotorClient,auth_utility: AuthUtility):
        self.__router = APIRouter(prefix="/session", tags=["session"])
        self.__user = user_sessions
        self.__auth_utility = auth_utility
        self.__user_session_metadata = mongo_db["user_session_metadata"]
        
        