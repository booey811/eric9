import json

from flask import jsonify, Blueprint, request

from ...services import monday
from ...tasks.monday.typeform import sync_typeform_response_with_monday
from ...cache import rq

typeform_bp = Blueprint('typeform', __name__, url_prefix='/monday/typeform')


@typeform_bp.route('/fetch-response-data', methods=['GET'])
@monday.monday_challenge
def fetch_response_data_from_typeform():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	rq.q_high(
		sync_typeform_response_with_monday,
		data['pulseId']
	)
	return jsonify({"status": "job queued"})