from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request 
from config.rate_limit_rules import RATE_LIMIT_RULES


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_conn, dispatch = None):
        super().__init__(app, dispatch)
        self.__redis_conn = redis_conn

    async def dispatch(self, request: Request, call_next):
       pass 
          


class RateLimiterResolver:
    def __init__(self, redis_conn, rules):
        self.__redis_conn = redis_conn
        self.__rules = rules 

    def get_rate_limiter(self, path: str):
        pass
    
    def __find_rate_limit_rule(self, path: str):
        for pref, endpoint_rules in self.__rules.items():
            if not path.startswith(pref):
                continue 
            suffix = path.removeprefix(pref)
            for pattern, rule in endpoint_rules.items():
                if self.__path_matches(suffix, pattern):
                    return rule 
        return None 
     
    def __path_matches(self, path, pattern):
        path_parts = path.strip("/").split("/")
        pattern_parts = pattern.strip("/").split("/")
        if len(path_parts) != len(pattern_parts):
            return False 
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                continue 
            if pattern_part != path_part:
                return False 
        return True 
    