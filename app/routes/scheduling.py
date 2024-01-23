import logging
import json

from flask import Blueprint, request, jsonify

from ..services.monday import monday_challenge, get_items
from ..models import MainModel
from ..services.motion import MotionClient
from ..utilities import users
from ..tasks import scheduling

log = logging.getLogger('eric')

scheduling_bp = Blueprint('scheduling', __name__, url_prefix="/scheduling")


@scheduling_bp.route("/repair-moves-group", methods=["POST"])
@monday_challenge
def handle_repair_group_change():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	main_id = data['pulseId']
	new_group_id = data['destGroupId']
	old_group_id = data['sourceGroupId']
	repair_group_ids = [user['repair_group_id'] for user in users.USER_DATA]

	log.debug(f"MainItem({main_id}) moved from group({old_group_id}) to group({new_group_id})")

	# if moving from non repair group to non repair group, do nothing
	if old_group_id not in repair_group_ids and new_group_id not in repair_group_ids:
		log.debug(f"MainItem({main_id}) moved from non repair group to non repair group, do nothing")
		return jsonify({'message': 'Not a repair group'}), 200

	item = get_items([main_id])[0]
	main = MainModel(item.id, item)
	repair_group_ids = [user['repair_group_id'] for user in users.USER_DATA]

	if old_group_id in repair_group_ids and main.model.motion_task_id:
		# moving from a repairer group - delete from this repairers schedule
		log.debug(f"MainItem({main_id}) moved from repair group({old_group_id})")
		user = users.User(repair_group_id=old_group_id)
		motion = MotionClient(user)
		motion.delete_task(main.model.motion_task_id)
		main.model.motion_task_id = None
		main.model.motion_scheduling_status = "Not In Repair Schedule"
		scheduling.schedule_update(old_group_id)

	if new_group_id in repair_group_ids:
		# repair has been moved a repairer's group, add motion task to new repairer schedule
		log.debug(f"MainItem({main_id}) moved to repair group({new_group_id})")
		user = users.User(repair_group_id=new_group_id)
		motion = MotionClient(user)
		try:
			task = motion.create_task(
				name=main.model.name,
				deadline=main.model.hard_deadline,
				description=main.model.requested_repairs,
				labels=['Repair']
			)
			log.debug(f"Created Motion Task({task['id']}) for MainItem({main_id})")
		except (scheduling.MissingDeadlineInMonday, AttributeError):
			log.debug(f"MainItem({main_id}) missing deadline, not creating motion task")
			main.model.save()
			return jsonify({'message': 'Missing Deadline'}), 200

		main.model.motion_task_id = task['id']
		main.model.motion_scheduling_status = 'Awaiting Sync'
		scheduling.schedule_update(new_group_id)

	main.model.save()
	return jsonify({'message': 'OK'}), 200


@scheduling_bp.route("/client-side-deadline-adjusted", methods=["POST"])
@monday_challenge
def handle_client_side_deadline_adjustment():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	group_id = data['groupId']

	repair_group_ids = [user['repair_group_id'] for user in users.USER_DATA]

	if group_id not in repair_group_ids:
		log.debug("CS Deadline Adjusted within non-repair group, do nothing")
		return jsonify({'message': 'Not a repair group'}), 200

	user = users.User(repair_group_id=group_id)
	motion = MotionClient(user)
	item = get_items([data['pulseId']])[0]
	main = MainModel(item.id, item)

	if main.model.motion_task_id:
		if not main.model.hard_deadline:
			log.debug(f"{main.model.name} missing deadline, deleting task")
			motion.delete_task(main.model.motion_task_id)
			main.model.motion_task_id = None
			main.model.motion_scheduling_status = "No Deadline"
			main.model.save()
			scheduling.schedule_update(group_id)
			return jsonify({'message': 'Missing Deadline'}), 200

		else:
			log.debug(f"Updating Motion Task({main.model.motion_task_id}) deadline for {main.model.hard_deadline}")
			motion.update_task(
				task_id=main.model.motion_task_id,
				deadline=main.model.hard_deadline
			)
			log.debug(f"Updated Motion Task({main.model.motion_task_id}) deadline for MainItem({main.id})")
			scheduling.schedule_update(group_id)
			main.model.motion_scheduling_status = 'Awaiting Sync'
			main.model.save()
			return jsonify({'message': 'OK'}), 200

	else:
		log.debug(f"MainItem({main.id}) missing motion task, Cannot update Task. Creating instead")
		try:
			task = motion.create_task(
				name=main.model.name,
				deadline=main.model.hard_deadline,
				description=main.model.requested_repairs,
				labels=['Repair']
			)
			log.debug(f"Created Motion Task({task['id']}) for MainItem({main.id})")
			main.model.motion_task_id = task['id']
			main.model.motion_scheduling_status = 'Awaiting Sync'
			main.model.save()
			scheduling.schedule_update(group_id)
		except (scheduling.MissingDeadlineInMonday, AttributeError):
			log.debug(f"MainItem({main.id}) missing deadline, not creating motion task")
			main.model.motion_scheduling_status = "No Deadline"
			main.model.save()
			return jsonify({'message': 'Missing Deadline'}), 200

	return jsonify({'message': 'Added Motion Task'}), 200
