from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os 
from db.db import Database
from routers.auth import AuthRouter, AuthUtility
from routers.session import SessionRouter
from routers.transcribe import TranscribeRouter

load_dotenv()

database = Database()
auth_utility = AuthUtility()

mongo_client = AsyncIOMotorClient(os.getenv("MONGO_DB_CONNECTION"))
mongo_db = mongo_client["caption_ai"]

routers = [
    AuthRouter(database, auth_utility).router,
    SessionRouter(database, mongo_db, auth_utility).router,
    TranscribeRouter(mongo_db, auth_utility).router,

]

class App:

    def __init__(self) -> None:
        self.__app = FastAPI()
        self.origins = [
            "http://localhost:3000",
            "http://localhost:8000",
        ]
        self.__add_middleware()
        self.__add_routers(routers)
    
    def __add_middleware(self):
        self.__app.add_middleware(
            CORSMiddleware,
            allow_origins=self.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

    def __add_routers(self, routers):
        for router in routers:
            self.__app.include_router(router)

    
    def get_app(self):
        return self.__app

app_instance = App()
app = app_instance.get_app()
