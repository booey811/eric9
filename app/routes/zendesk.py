import json

from flask import Blueprint, request, jsonify

from ..cache.rq import q_high
from ..tasks import sync_platform

import config

conf = config.get_config()

zendesk_bp = Blueprint('zendesk', __name__, url_prefix='/zendesk')


@zendesk_bp.route('/index', methods=['POST', 'GET'])
def zendesk_creates_monday_ticket():
	data = request.get_data().decode()
	data = json.loads(data)
	ticket_id = data['id']
	event = data['event']

	if event == 'sync_item':
		if conf.CONFIG in ('DEVELOPMENT', 'TESTING'):
			sync_platform.sync_to_monday(ticket_id)
		else:
			q_high.enqueue(
				sync_platform.sync_to_monday,
				ticket_id
			)
	else:
		raise ValueError(f"Invalid event: {event}")

	return jsonify({'status': 'success'}, 200)
