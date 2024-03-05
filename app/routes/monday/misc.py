import logging
from flask import Blueprint, jsonify, request
import json

from ...cache.rq import q_low
from ...services import monday
from ...tasks.monday import web_bookings
import config

conf = config.get_config()

log = logging.getLogger('eric')

monday_misc_bp = Blueprint('monday_misc', __name__, url_prefix='/monday/misc')


@monday_misc_bp.route('/enquiry', methods=['POST'])
@monday.monday_challenge
def push_web_enquiry_to_zendesk():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		web_bookings.push_web_enquiry_to_zendesk(data['pulseId'])
	else:
		q_low.enqueue(
			web_bookings.push_web_enquiry_to_zendesk,
			data['pulseId']
		)

	return jsonify({'message': 'OK'}), 200
