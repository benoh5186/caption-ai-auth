from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


load_dotenv()


class App:

    def __init__(self) -> None:
        self.__app = FastAPI()
        self.origins = [
            "http://localhost:8000"
        ]
    
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