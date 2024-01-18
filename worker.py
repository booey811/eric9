from rq import Worker

from app.cache import get_redis_connection
from app.cache.rq import queues


# When running `with_scheduler=True` this is necessary
if __name__ == '__main__':
    worker = Worker(queues=queues, connection=get_redis_connection())
    worker.work(with_scheduler=True)
