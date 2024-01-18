import logging
import json

from flask import Blueprint, request, jsonify

from app.services.monday import monday_challenge, get_items
from app.models import MainModel
from app.services import motion
from app.utilities import users

log = logging.getLogger('eric')

scheduling = Blueprint('scheduling', __name__, url_prefix="/scheduling")


@scheduling.route("/repair-moves-group")
@monday_challenge
def handle_repair_group_change():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	main_id = data['pulseId']
	new_group_id = data['destGroupId']
	old_group_id = data['new_group56509']

	repair_group_ids = [user.repair_group_id for user in users.USER_DATA]

	if old_group_id in repair_group_ids:
		# Repair has been removed from repairer list, delete motion task
		pass

	if new_group_id in repair_group_ids:
		# repair has been moved a repairer's group, add motion task
		pass

	item = get_items([main_id])[0]
	main = MainModel(item)

