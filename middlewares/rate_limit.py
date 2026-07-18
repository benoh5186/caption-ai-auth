from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request 
from config.rate_limit_rules import RATE_LIMIT_RULES


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rule = self.__find_rate_limit_rules(request.url.path, RATE_LIMIT_RULES)
        if rule is None:
            await call_next()
        #abstract factory class for rate limitters to be implemented
          

    def __find_rate_limit_rules(self, path, rate_limit_rules):
        for pref, endpoint_rules in rate_limit_rules.items():
            if not path.startswith(pref):
                continue 
            suffix = path.removeprefix(pref) 
            for pattern, rule in endpoint_rules.items():
                if self.__path_matches(pattern, suffix):
                    return rule 
        return None  

    def __path_matches(self, pattern, path):
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return False 
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                continue 
            if pattern_part != path_part:
                return False 
        return True
