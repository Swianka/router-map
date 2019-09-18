import redis
import time
from django.conf import settings


class RedisClient:
    def __init__(self):
        self.__redis = redis.Redis(host=settings.REDIS_HOST)

    def set_last_update_time(self):
        self.__redis.set('last_update_time', time.time())

    def get_last_update_time(self):
        return self.__redis.get('last_update_time')


redis_client = RedisClient()
