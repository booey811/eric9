from rq import Worker

from app.cache import get_redis_connection
from app.cache.rq import q_high, q_ai_results, q_low, q_med


# When running `with_scheduler=True` this is necessary
if __name__ == '__main__':
    worker = Worker(
        queues=[
            q_high,
            q_ai_results,
            q_med,
            q_low,
        ],
        connection=get_redis_connection()
    )
    worker.work(with_scheduler=True)
