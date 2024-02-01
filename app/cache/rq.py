import datetime

from rq import Queue
from rq.registry import FailedJobRegistry

from .redis_client import get_redis_connection


a_sync = True
# if conf.DEBUG:
#     a_sync = False

q_low = Queue('low', connection=get_redis_connection(), is_async=a_sync)
q_med = Queue('medium', connection=get_redis_connection(), is_async=a_sync)
q_high = Queue('high', connection=get_redis_connection(), is_async=a_sync)
q_ai_results = Queue('ai_results', connection=get_redis_connection(), is_async=a_sync)


def remove_failed_jobs():
	for q in (q_low, q_med, q_high, q_ai_results):
		print(q)
		finished_reg = q.finished_job_registry
		for job in finished_reg.get_job_ids():
			print(job)
			finished_reg.remove(job)
		failed_job_registry = FailedJobRegistry(queue=q)
		for job_id in failed_job_registry.get_job_ids():
			print(job_id)
			failed_job_registry.remove(job_id, delete_job=True)
