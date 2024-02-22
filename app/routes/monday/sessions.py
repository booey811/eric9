import json

from flask import jsonify, request, Blueprint

from ...services import gcal, monday
from ...cache.rq import q_low
from ... import tasks

sessions_bp = Blueprint('sessions', __name__, url_prefix='/repair-sessions')


@sessions_bp.route('/map-to-gcal', methods=['POST'])
@monday.monday_challenge
def map_session_to_gcal():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		tasks.monday.sessions.map_session_to_gcal,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200

