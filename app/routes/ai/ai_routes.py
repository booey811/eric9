import logging
import json

from flask import Blueprint, jsonify, request

import config
from ...services import openai as ai, monday
from ...services.monday import monday_challenge, items
from ...utilities import users

log = logging.getLogger('eric')

conf = config.get_config()

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

	if user.name != 'safan':
		log.debug("Not Safan, no translation required")
		return jsonify({'message': 'Not Safan'}), 200

	run = ai.utils.create_and_run_thread(
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

	ai.utils.check_run(thread_id=run.thread_id, run_id=run.id,
					   success_endpoint=f'{conf.APP_URL}/ai/translator-results/')

	return jsonify({'message': 'AI Translation Requested'}), 200


@ai_bp.route("/translator-results/", methods=["POST"])
def process_ai_translation():
	log.debug("AI Translation Route")
	data = request.get_json()

	message = ai.utils.list_messages(data['thread_id'], limit=1).data[0].content[0].text.value

	main = items.MainItem(data['main_id'], monday.api.client.get_api_items([data['main_id']])[0])

	main.add_update(
		body=f"!- Beta:Notes Updates -!\n\n{message}",
		thread_id=data['notes_thread']
	)

	return jsonify({'message': 'AI Translation Message Added to Monday Thread'}), 200
