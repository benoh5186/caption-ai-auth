import os
import json
from datetime import datetime, timezone
from typing import Any

import pymysql
from pymysql.err import IntegrityError
from pymysql.cursors import DictCursor

from schemas.user import UserAlreadyExistsError, UserCreate, UserLogin, UserSchema, UserStatus


class Database:
    def __init__(self) -> None:
        self.__host = os.getenv("MYSQLDB_HOST")
        self.__port = int(os.getenv("MYSQLDB_PORT", "3306"))
        self.__user = os.getenv("MYSQLDB_USER")
        self.__password = os.getenv("MYSQLDB_PASSWORD")
        self.__database = os.getenv("MYSQLDB_DB")
        self.__connection = None

    def start_database(self) -> None:
        self.__connection = pymysql.connect(
            host=self.__host,
            port=self.__port,
            user=self.__user,
            password=self.__password,
            database=self.__database,
            cursorclass=DictCursor,
            ssl={'ssl': True},
            autocommit=False,
        )

    def ensure_connection(self) -> None:
        if self.__connection is None:
            self.start_database()
            return

        try:
            self.__connection.ping(reconnect=True)
        except pymysql.MySQLError:
            self.start_database()

    def __fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        self.ensure_connection()
        with self.__connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def __fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.ensure_connection()
        with self.__connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def __execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        return_lastrowid: bool = False,
    ) -> int:
        self.ensure_connection()
        with self.__connection.cursor() as cursor:
            affected_rows = cursor.execute(query, params or ())
            inserted_id = cursor.lastrowid
        self.__connection.commit()
        if return_lastrowid:
            return inserted_id
        return affected_rows

    def create_user(self, user: UserCreate) -> UserSchema:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        metadata = self.__to_json(user.metadata)

        insert_query = """
            INSERT INTO users (
                email, password_hash, full_name, status, role,
                created_at, updated_at, last_login_at, email_verified_at,
                auth_provider, provider_id, phone, deleted_at, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            inserted_id = self.__execute_query(
                insert_query,
                (
                    str(user.email),
                    user.password_hash,
                    user.full_name,
                    user.status.value,
                    user.role,
                    now,
                    now,
                    None,
                    None,
                    user.auth_provider,
                    user.provider_id,
                    user.phone,
                    None,
                    metadata,
                ),
                return_lastrowid=True,
            )
        except IntegrityError as exc:
            self.__connection.rollback()
            if exc.args and exc.args[0] == 1062:
                raise UserAlreadyExistsError(str(user.email)) from exc
            raise
        created_user = self.get_user_by_id(str(inserted_id))
        if created_user is None:
            raise RuntimeError("Failed to read user after insert.")
        return created_user

    def get_user_by_id(self, user_id: str) -> UserSchema | None:
        query = "SELECT * FROM users WHERE id = %s AND deleted_at IS NULL LIMIT 1"
        row = self.__fetch_one(query, (user_id,))
        return self.__row_to_user_schema(row)

    def get_user_by_email(self, email: str | UserLogin) -> UserSchema | None:
        email_value = self.__extract_email(email)
        query = "SELECT * FROM users WHERE email = %s AND deleted_at IS NULL LIMIT 1"
        row = self.__fetch_one(query, (email_value,))
        return self.__row_to_user_schema(row)

    def get_user_by_provider(self, auth_provider: str, provider_id: str) -> UserSchema | None:
        query = """
            SELECT * FROM users
            WHERE auth_provider = %s AND provider_id = %s AND deleted_at IS NULL
            LIMIT 1
        """
        row = self.__fetch_one(query, (auth_provider, provider_id))
        return self.__row_to_user_schema(row)

    def update_user_profile(
        self,
        user_id: str,
        full_name: str | None = None,
        phone: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            UPDATE users
            SET full_name = %s, phone = %s, metadata = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(
            query,
            (
                full_name,
                phone,
                self.__to_json(metadata or {}),
                now,
                user_id,
            ),
        )
        return affected > 0

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            UPDATE users
            SET password_hash = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(query, (password_hash, now, user_id))
        return affected > 0

    def mark_email_verified(self, user_id: str, verified_at: datetime | None = None) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        verified_at_value = verified_at or now
        query = """
            UPDATE users
            SET email_verified_at = %s, updated_at = %s, status = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(
            query,
            (verified_at_value, now, UserStatus.ACTIVE.value, user_id),
        )
        return affected > 0

    def update_last_login(self, user_id: str, at: datetime | None = None) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        last_login_at = at or now
        query = """
            UPDATE users
            SET last_login_at = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(query, (last_login_at, now, user_id))
        return affected > 0

    def update_user_status(self, user_id: str, status: UserStatus) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            UPDATE users
            SET status = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(query, (status.value, now, user_id))
        return affected > 0

    def update_user_role(self, user_id: str, role: str) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            UPDATE users
            SET role = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(query, (role, now, user_id))
        return affected > 0

    def soft_delete_user(self, user_id: str, deleted_at: datetime | None = None) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        deleted_at_value = deleted_at or now
        query = """
            UPDATE users
            SET deleted_at = %s, status = %s, updated_at = %s
            WHERE id = %s AND deleted_at IS NULL
        """
        affected = self.__execute_query(
            query,
            (deleted_at_value, UserStatus.DELETED.value, now, user_id),
        )
        return affected > 0
    
    def increase_sessions_creation_count(self, user_id: str) -> bool:
        max_sessions = 10
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session_count = self.__get_sessions_count(user_id)
        if session_count == max_sessions:
            raise Exception()
        query = """
            UPDATE user_sessions_count
            SET
            session_count = session_count + 1,
            updated_at = %s
            WHERE user_id = %s
        """
        affected = self.__execute_query(query, (now, user_id))
        return affected > 0
    
    def decrease_sessions_creation_count(self, user_id: str) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = """
            UPDATE user_sessions_count
            SET
            session_count = session_count - 1,
            updated_at = %s
            WHERE user_id = %s
        """
        affected = self.__execute_query(query, (now, user_id))
        return affected > 0 
    
    def __get_sessions_count(self, user_id: str) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        insert_query = """
            INSERT INTO user_sessions_count (user_id, session_count, created_at, updated_at)
            VALUES (%s, 0, %s, %s)
            ON DUPLICATE KEY UPDATE
                updated_at = updated_at
        """
        self.__execute_query(insert_query, (user_id, now, now))

        query = """
            SELECT session_count
            FROM user_sessions_count
            WHERE user_id = %s
            LIMIT 1
        """
        row = self.__fetch_one(query, (user_id,))
        if row is None:
            raise RuntimeError(f"Failed to load session count for user_id={user_id}")
        return int(row.get("session_count", 0))

    def list_users(
        self,
        status: UserStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserSchema]:
        if status is None:
            query = """
                SELECT * FROM users
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            rows = self.__fetch_all(query, (limit, offset))
        else:
            query = """
                SELECT * FROM users
                WHERE status = %s AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            rows = self.__fetch_all(query, (status.value, limit, offset))
        return [self.__row_to_user_schema(row) for row in rows if row is not None]

    def email_exists(self, email: str | UserLogin) -> bool:
        email_value = self.__extract_email(email)
        query = "SELECT 1 AS exists_flag FROM users WHERE email = %s AND deleted_at IS NULL LIMIT 1"
        row = self.__fetch_one(query, (email_value,))
        return row is not None

    def authenticate_user(self, user_login: UserLogin, password_hash: str) -> UserSchema | None:
        query = """
            SELECT * FROM users
            WHERE email = %s AND password_hash = %s AND deleted_at IS NULL
            LIMIT 1
        """
        row = self.__fetch_one(query, (str(user_login.email), password_hash))
        return self.__row_to_user_schema(row)

    @staticmethod
    def __to_json(value: dict[str, Any]) -> str:
        return json.dumps(value)

    @staticmethod
    def __to_dict(value: Any) -> dict[str, Any]:

        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
                return decoded if isinstance(decoded, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def __row_to_user_schema(self, row: dict[str, Any] | None) -> UserSchema | None:
        if row is None:
            return None

        row["status"] = row.get("status") or UserStatus.INVITED.value
        row["metadata"] = self.__to_dict(row.get("metadata"))
        return UserSchema.model_validate(row)

    @staticmethod
    def __extract_email(email: str | UserLogin) -> str:
        if isinstance(email, UserLogin):
            return str(email.email)
        return email
