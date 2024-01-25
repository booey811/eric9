import logging
import json

from flask import Blueprint, jsonify, request

from ..services.openai import utils as ai
from ..models import MainModel
from ..services.monday import monday_challenge
from ..utilities import users
from ..cache.rq import q_high
from ..tasks.monday import updates
from .. import conf

log = logging.getLogger('eric')

ai_bp = Blueprint('ai', __name__, url_prefix="/ai")


@ai_bp.route("/request-translation/", methods=["POST"])
@monday_challenge
def process_ai_translation_request():
	log.debug("AI Translation Requested Route")

	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	try:
		user = users.User(monday_id=data['userId'])
	except ValueError:
		log.debug("No User Found")
		return jsonify({'message': 'No User Found'}), 200

	if user.name not in ('safan', 'gabe'):
		log.debug("Not Safan, no translation required")
		return jsonify({'message': 'Not Safan'}), 200

	run = ai.create_and_run_thread(
		assistant_id=conf.OPEN_AI_ASSISTANTS['translator'],
		messages=[
			data['textBody']
		],
		metadata={
			"main_id": data['pulseId'],
			"notes_thread": data['updateId'],
			"endpoint": f'{conf.APP_URL}/ai/translator-results/'
		}
	)

	ai.check_run(thread_id=run.thread_id, run_id=run.id, success_endpoint=f'{conf.APP_URL}/ai/translator-results/')

	return jsonify({'message': 'AI Translation Requested'}), 200


@ai_bp.route("/translator-results/", methods=["POST"])
def process_ai_translation():
	log.debug("AI Translation Route")
	data = request.get_json()

	message = ai.list_messages(data['thread_id'], limit=1).data[0].content[0].text.value

	q_high.enqueue(
		f=updates.add_message_to_update_thread,
		kwargs={
			"update_thread_id": data['notes_thread'],
			"update": message,
			"title": "!- Beta:Notes Updates -!",
			"main_id": data['main_id']
		}
	)

	return jsonify({'message': 'AI Translation Message Added to Monday Thread'}), 200
