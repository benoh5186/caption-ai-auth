import hashlib
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse


class AuthUtility:
    def __init__(self) -> None:
        self._secret = os.getenv("JWT_SECRET_KEY")
        self._algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self._cookie_name = "session_token"
        self._session_minutes = 5
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
        
    def __allow_request(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_seconds = window_seconds - now 
        times = self._requests[key]
        while times and times[0] <= window_seconds:
            times.popleft()
        if len(times) > max_requests:
            wait_time = max(1, int(times[0] + window_seconds - now))
            return False, wait_time
        times.append(now)
        return True, 0
    

    def enforce_rate_limit(
            self,  
            max_requests: int, 
            window_seconds: int, 
            route_name: str):
        client = self.__client_identifier()
        key = f"{route_name}: {client}"
        allowed, wait_time = self.__allow_request(key=key, max_requests=max_requests, window_seconds=window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded for {route_name}. "
                    f"Try again in about {wait_time} seconds."
                ),
            )

    @staticmethod
    def __client_identifier(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"




class AuthRouter:
    def __init__(self, mongo_db) -> None:
        self.__router = APIRouter(prefix="/auth", tags=["auth"])
        self.__users = mongo_db["users"]
        self.__session_utility = AuthUtility()
        self.__register_routes()

    def __register_routes(self) -> None:
        self.__router.add_api_route("/signup", self.signup, methods=["POST"])
        self.__router.add_api_route("/login", self.login, methods=["POST"])
        self.__router.add_api_route("/dashboard", self.dashboard, methods=["GET"])

    async def signup(self, request: Request):
        payload = await request.json()
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            raise HTTPException(status_code=400, detail="email and password are required.")

        existing_user = await self.__users.find_one({"email": email})
        if existing_user:
            raise HTTPException(status_code=409, detail="User already exists.")

        password_hash = self.__hash_password(password)
        user_doc = {
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc),
        }
        insert_result = await self.__users.insert_one(user_doc)
        user_id = str(insert_result.inserted_id)

        token = self.__session_utility.create_token(user_id=user_id, email=email)
        response = JSONResponse(
            status_code=201,
            content={"message": "Signup successful.", "user_id": user_id},
        )
        self.__session_utility.set_session_cookie(response, token)
        return response

    async def login(self, request: Request):
        payload = await request.json()
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            raise HTTPException(status_code=400, detail="email and password are required.")

        user = await self.__users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        password_hash = self.__hash_password(password)
        if user.get("password_hash") != password_hash:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        user_id = str(user["_id"])
        token = self.__session_utility.create_token(user_id=user_id, email=email)
        response = JSONResponse(content={"message": "Login successful."})
        self.__session_utility.set_session_cookie(response, token)
        return response

    async def dashboard(self, request: Request):
        session_payload = self.__session_utility.require_session(request)
        return {
            "message": "Dashboard access granted.",
            "user": {
                "user_id": session_payload.get("sub"),
                "email": session_payload.get("email"),
            },
        }

    @staticmethod
    def __hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


    @property
    def router(self) -> APIRouter:
        return self.__router
