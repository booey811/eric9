import logging
from functools import wraps

from flask import request, jsonify

from ...errors import EricError
from . import items, api

log = logging.getLogger('eric')


def monday_challenge(func):
	@wraps(func)
	def decorated_function(*args, **kwargs):
		# Check if the incoming request has a 'challenge' key
		challenge = request.json.get('challenge') if request.json else None
		if challenge:
			# If it's a challenge, return the challenge code back to monday.com
			return jsonify({'challenge': challenge})
		# Otherwise, proceed with the actual processing
		return func(*args, **kwargs)

	return decorated_function


class MondayError(EricError):

	def __str__(self):
		return f"Monday Error: {str(self.m)}"

	def __init__(self, message):
		self.m = message

