import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor


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

    def __execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> int:
        self.ensure_connection()
        with self.__connection.cursor() as cursor:
            affected_rows = cursor.execute(query, params or ())
        self.__connection.commit()
        return affected_rows
