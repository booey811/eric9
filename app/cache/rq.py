from rq import Queue

from .redis_client import get_redis_connection


a_sync = True
# if conf.DEBUG:
#     a_sync = False

queues = {
    'low': Queue('low', connection=get_redis_connection(), is_async=a_sync),
    'medium': Queue('medium', connection=get_redis_connection(), is_async=a_sync),
    'high': Queue('high', connection=get_redis_connection(), is_async=a_sync),
}