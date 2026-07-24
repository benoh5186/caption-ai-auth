import hashlib
import bcrypt 
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from db.db import Database
from schemas.user import UserAlreadyExistsError, UserCreate, UserLogin, UserSignup


class AuthUtility:
    def __init__(self) -> None:
        self._secret = os.getenv("JWT_SECRET_KEY")
        self._algorithm = os.getenv("JWT_ALGORITHM")
        self._cookie_name = "session_token"
        self._session_minutes = 60
        self._requests = defaultdict(deque)

    def create_token(self, user_id: str, email: str) -> str:
        if not self._secret:
            raise HTTPException(status_code=500, detail="JWT_SECRET_KEY is not configured.")

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._session_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expires_at,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def set_session_cookie(self, response: JSONResponse, token: str) -> None:
        response.set_cookie(
            key=self._cookie_name,
            value=token,
            max_age=self._session_minutes * 60,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )

    def require_session(self, request: Request) -> dict:
        if not self._secret:
            raise HTTPException(status_code=500, detail="JWT_SECRET_KEY is not configured.")

        token = request.cookies.get(self._cookie_name)
        if not token:
            raise HTTPException(status_code=401, detail="No active session.")

        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Session expired.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid session token.") from exc
        


class AuthRouter:
    def __init__(self, user: Database, auth_utility: AuthUtility) -> None:
        self.__router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
        self.__user = user
        self.__auth_utility = auth_utility
        self.__register_routes()

    def __register_routes(self) -> None:
        self.__router.add_api_route("/signup", self.signup, methods=["POST"])
        self.__router.add_api_route("/login", self.login, methods=["POST"])
        self.__router.add_api_route("/authenticate", self.authenticate, methods=["GET"])

    async def signup(self, signup: UserLogin, request: Request):
        user_create = UserCreate(
            email=signup.email,
            password_hash=self.__hash_password(signup.password),
        )

        try:
            created_user = self.__user.create_user(user_create)
        except UserAlreadyExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        token = self.__auth_utility.create_token(
            user_id=created_user.id,
            email=str(created_user.email),
        )
        response = JSONResponse(
            status_code=201,
            content={"message": "Signup successful.", "user_id": created_user.id},
        )
        self.__auth_utility.set_session_cookie(response, token)
        return response
    
    async def authenticate(self, request: Request):
        self.__auth_utility.require_session(request)
        return 


    async def login(self, login: UserLogin, request: Request):
        user = self.__user.get_user_by_email(login.email)
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        
        if not self.__verify_password(login.password, user.password_hash):
            raise HTTPException(status_code=401, detail='Invalid email or password')

        self.__user.update_last_login(user.id)
        token = self.__auth_utility.create_token(user_id=user.id, email=str(user.email))
        response = JSONResponse(content={"message": "Login successful."})
        self.__auth_utility.set_session_cookie(response, token)
        return response


    @staticmethod
    def __hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def __verify_password(login_password: str, db_password: str) -> bool:
        login_password_encoded = login_password.encode("utf-8")
        db_password_encoded = db_password.encode("utf-8")
        return bcrypt.checkpw(login_password_encoded, db_password_encoded)

    @property
    def router(self) -> APIRouter:
        return self.__router
