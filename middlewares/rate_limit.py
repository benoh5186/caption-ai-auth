from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from config.rate_limit_rules import RATE_LIMIT_RULES
from services.rate_limiter import TokenBucket, LeakyBucket


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_conn, rules, dispatch = None):
        super().__init__(app, dispatch)
        self.__redis_conn = redis_conn
        self.__rules = rules

    async def dispatch(self, request: Request, call_next):
       client_ip = self.__get_client_ip(request)
       if client_ip is None:
           raise HTTPException(status_code=400, detail="Could not identify the client")
       rate_limit_resolver = RateLimiterResolver(self.__redis_conn, self.__rules, client_ip)
       rate_limiter = rate_limit_resolver.get_rate_limiter(request.url.path)
       if rate_limiter is None:
           await call_next()
       if await rate_limiter.request_allowed():
           await call_next()
       raise HTTPException(status_code=429)
           

    @staticmethod
    def __get_client_ip(request: Request):
        if request.client and request.client.host:
            return request.client.host
        return None
          


class RateLimiterResolver:
    __DEFAULT_RATE_LIMITER_ARG = {
        "token_bucket" : {
            "max_tokens" : 10,
            "refill_rate" : 10 / 60
        },
        "leaky_bucket" : {
            "max_bucket_size" : 5,
            "leak_rate" : 5 / 30
        }
    }
    def __init__(self, redis_conn, rules, client_ip):
        self.__redis_conn = redis_conn
        self.__rules = rules 
        self.__client_ip = client_ip 

    def get_rate_limiter(self, path: str):
        default_token_bucket = self.__DEFAULT_RATE_LIMITER_ARG["token_bucket"]
        default_leaky_bucket = self.__DEFAULT_RATE_LIMITER_ARG["leaky_bucket"]
        pattern, rule = self.__find_rate_limit_rule(path=path)
        key = self.__make_key(pattern)
        if rule is None:
            return None 
        type = rule.get("type")
        if type == "token_bucket":
            max_tokens = rule.get("max_tokens", default_token_bucket["max_tokens"])
            refill_rate = rule.get("refill_rate", default_token_bucket["refill_rate"])
            return TokenBucket(redis_conn=self.__redis_conn, key=key, refill_rate=refill_rate, max_tokens=max_tokens)
        if type == "leaky_bucket":
            max_bucket_size = rule.get("max_bucket_size", default_leaky_bucket["max_bucket_size"])
            leak_rate = rule.get("leak_rate", default_leaky_bucket["leak_rate"])
            return LeakyBucket(redis_conn=self.__redis_conn, key=key, leak_rate=leak_rate, max_bucket_size=max_bucket_size)
        return TokenBucket(redis_conn=self.__redis_conn, key=key, refill_rate=default_token_bucket["refill_Rate"], max_tokens=default_token_bucket["max_tokens"])
            
    def __make_key(self, pattern):
        return f"{self.__client_ip}:{pattern}"
    
    def __find_rate_limit_rule(self, path: str):
        for pref, endpoint_rules in self.__rules.items():
            if not path.startswith(pref):
                continue 
            suffix = path.removeprefix(pref)
            for pattern, rule in endpoint_rules.items():
                if self.__path_matches(suffix, pattern):
                    return pattern, rule 
        return None, None 
     
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
    