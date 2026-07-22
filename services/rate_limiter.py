from redis.asyncio import Redis 

class TokenBucket:
    """
    token bucket rate limiting algorithm which has one public method: run() which calls call_next from fastapi middleware.
    Else, it throws an Exception(custom exception to be implemented)
    """
    def __init__(self, redis_conn: Redis, key: str, refill_rate: int, max_tokens: int):
        self.__redis = redis_conn
        self.__key = key 
        self.__refill_rate = refill_rate 
        self.__max_tokens = max_tokens

    async def request_allowed(self):
        if await self.__check_bucket():
            return True
        return False 

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
                     
                redis.call("HSET", key, 'tokens', fields['tokens'], 'last_refill', now)
                redis.call("EXPIRE", key, math.ceil(max_tokens / refill_rate) + 1)
                return allowed
                
            end 
            
            function refill(bucket)
                elapsed = now - bucket['last_refill']
                local tokens = bucket[tokens] + (elapsed * refill_rate)
                bucket['tokens'] = math.min(max_tokens, tokens)
                bucket['last_refill'] = now
                return tokens
            end 
            token_bucket()
        """, 1, self.__key, self.__max_tokens, self.__refill_rate) 
        return result 

class LeakyBucket:
    def __init__(self, redis_conn: Redis, key: str, leak_rate: int, max_bucket_size: int):
        self.__redis = redis_conn
        self.__key = key
        self.__leak_rate = leak_rate
        self.__max_bucket_size = max_bucket_size

    async def request_allowed(self):
        if await self.__check_bucket():
            return True 
        return False 
        
    async def __check_bucket(self):
        result = await self.__redis.eval("""
                    local key = KEYS[1]
                    local leak_rate = tonumber(ARGV[1])
                    local max_bucket_size = tonumber(ARGV[2])
                    local now = tonumber(ARGV[3])
                                   
                    function leaky_bucket()
                        local data = redis.call("HGETALL", key)
                        local fields = {}
                        local allowed = 0
                        if (#data > 0)    
                        then   
                            for i = 1, #data, 2
                            do
                                fields[data[i]] = data[i + 1]    
                            end
                            refill(fields)
                            if (fields['bucket_size'] == max_bucket_size)
                            then 
                                allowed = 1
                            else
                                fields['bucket_size'] = fields['bucket_size'] - 1 
                            end 
                        else
                            fields['bucket_size'] = 0 
                            fields['last_leak'] = now
                        end
                        redis.call('HSET', key, 'bucket_size', fields['bucket_size'], 'last_leak', now)
                        redis.call('EXPIRE', key, math.ceil(max_bucket_size / leak_rate) + 1)
                                         
                        return allowed
                    end
                                         
                    function refill(bucket)
                        local elapsed = now - bucket['last_leak']
                        local new_bucket = bucket['bucket_size'] - (elapsed * leak_rate)
                        bucket['bucket_size'] = math.max(0, new_bucket)
                        bucket['last_refill'] = now 
                    end
                """, 1, self.__key, self.__leak_rate, self.__max_bucket_size)
        return result 
