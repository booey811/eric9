import logging
import json

from flask import Blueprint, request, jsonify

from app.services.monday import monday_challenge, get_items
from app.models import MainModel
from app.services.motion import MotionClient
from app.utilities import users
from app.tasks import scheduling
from . import exceptions

log = logging.getLogger('eric')

scheduling_bp = Blueprint('scheduling', __name__, url_prefix="/scheduling")


@scheduling_bp.route("/repair-moves-group", methods=["POST"])
@monday_challenge
def handle_repair_group_change():
	try:
		webhook = request.get_data()
		data = webhook.decode('utf-8')
		data = json.loads(data)['event']
		main_id = data['pulseId']
		new_group_id = data['destGroupId']
		old_group_id = data['new_group56509']
		item = get_items([main_id])[0]
		main = MainModel(item)
		repair_group_ids = [user.repair_group_id for user in users.USER_DATA]

		if old_group_id in repair_group_ids:
			# moving from a repairer group - delete from this repairers schedule
			user = users.User(repair_group_id=old_group_id)
			motion = MotionClient(user)
			motion.delete_task(main.model.motion_task_id)
			scheduling.schedule_update(old_group_id)

		if new_group_id in repair_group_ids:
			# repair has been moved a repairer's group, add motion task to new repairer schedule
			user = users.User(repair_group_id=new_group_id)
			motion = MotionClient(user)
			if not main.model.hard_deadline:
				raise scheduling.MissingDeadlineInMonday

			task = motion.create_task(
				name=main.model.name,
				deadline=main.model.hard_deadline,
				description=main.model.requested_repairs,
				labels=['Repair']
			)
			main.model.motion_task_id = task['id']
			main.model.motion_scheduling_status = 'Awaiting Sync'
			scheduling.schedule_update(new_group_id)

		main.model.save()

	except Exception as e:
		raise exceptions.ErrorInRoute(e, request.path)


