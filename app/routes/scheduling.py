import logging
import json

from flask import Blueprint, request, jsonify

from app.services.monday import monday_challenge, get_items
from app.models import MainModel
from app.services import motion

log = logging.getLogger('eric')

scheduling = Blueprint('scheduling', __name__, url_prefix="/scheduling")


@scheduling.route("/add_repair")
@monday_challenge
def add_repair_to_schedule():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	main_id = data['pulseId']
	item = get_items([main_id])[0]

	main = MainModel(item)

	if main.model.motion_task_id:
		pass
	else:
		motion.client.create_task(
			name=main.model.name,
			deadline=main.model.hard_deadline,
			description=main.model.requested_repairs,
		)
	return jsonify({'result': 'Added to Schedule'}), 200


