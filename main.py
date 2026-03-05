from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os 


load_dotenv()

mongo_client = AsyncIOMotorClient(os.getenv("MONGO_DB_CONNECTION"))
mongo_db = mongo_client["caption_ai"]


class App:

    def __init__(self) -> None:
        self.__app = FastAPI()
        self.origins = [
            "http://localhost:8000"
        ]
        self.__add_middleware()
    
    def __add_middleware(self):
        self.__app.add_middleware(
            CORSMiddleware,
            allow_origins=self.origins,
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