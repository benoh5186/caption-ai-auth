from redis.asyncio import Redis 

class TokenBucket():
    """
    token bucket rate limiting algorithm which has one public method: run() which calls call_next from fastapi middleware.
    Else, it throws an Exception(custom exception to be implemented-==[p]=890u)
    """
    def __init__(self, redis_conn: Redis, key: str, refill_rate: int, max_tokens: int):
        self.__redis = redis_conn
        self.__key = key 
        self.__refill_rate = refill_rate 
        self.__max_tokens = max_tokens

    async def run(self, call_next):
        if await self.__check_bucket():
            await call_next()
        else:
            raise Exception()

    async def __check_bucket(self):
        result = await self.__redis.eval("""
            local key = KEYS[1]
            local max_tokens = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            function token_bucket()
                local data = redis.call('HGETALL', key)
                local fields = {}
                local allowed = 0
                if (#data > 0) 
                then 
                    for i = 1, #data, 2
                    do
                        fields[data[i]] = data[i + 1]
                    end 
                    refill(fields)
                    if (fields['tokens'] <= 0)
                    then 
                        allowed = 1
                    else
                        fields['tokens'] = fields['tokens'] - 1
                    end 
                else
                    fields['tokens'] = max_tokens - 1 
                    fields['last_refill'] = now 
                end 
                     
                redis.call("HSET", key, 'tokens', fields['tokens'], 'last_refill', fields['last_refill'])
                return allowed
                
            end 
            
            function refill(bucket)
                elapsed = now - bucket['last_refill']
                local tokens = bucket[tokens] + (elapsed * refill_rate)
                bucket['tokens'] = math.min(max_tokens, tokens)
                bucket['last_refill'] = now
                return tokens
            end 
        """, 1, self.__key, self.__max_tokens, self.__refill_rate) 
        return result 

