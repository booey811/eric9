from rq import Queue

from .redis_client import get_redis_connection


a_sync = True
# if conf.DEBUG:
#     a_sync = False

q_low = Queue('low', connection=get_redis_connection(), is_async=a_sync)
q_med = Queue('medium', connection=get_redis_connection(), is_async=a_sync)
q_high = Queue('high', connection=get_redis_connection(), is_async=a_sync)
q_ai_results = Queue('ai_results', connection=get_redis_connection(), is_async=a_sync)
