import json

from ...errors import EricError
from ...cache import get_redis_connection


def save_metadata(meta, key_name):
	"""saves current app metadata to cache for retrieval if needed"""
	key = f"slack_meta:{key_name}"
	get_redis_connection().set(
		name=key,
		value=json.dumps(meta),
		ex=86400  # 1 day
	)
	return True


class SlackDataError(EricError):

	def __str__(self):
		return f"Slack Data Error: {self.message}"
