import logging
import json

from flask import Blueprint, request, jsonify

from ..services.monday import monday_challenge, items
from ..services import monday
from ..services.motion import MotionClient, MotionError
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
	all_users = [users.User(_['name']) for _ in users.USER_DATA]
	repair_group_ids = [
		user.repair_group_id for user in all_users if user.name in ('safan', 'andres')
	]
	log.debug(f"MainItem({main_id}) moved from group({old_group_id}) to group({new_group_id})")

	# if moving from non repair group to non repair group, do nothing
	if old_group_id not in repair_group_ids and new_group_id not in repair_group_ids:
		log.debug(f"MainItem({main_id}) moved from non repair group to non repair group, do nothing")
		return jsonify({'message': 'Not a repair group'}), 200

	item = monday.api.get_api_items([main_id])[0]
	main = items.MainItem(item['id'], item)

	if old_group_id in repair_group_ids and main.motion_task_id.value:
		# moving from a repairer group
		if new_group_id == "new_group22081":  # under repair group ID
			# moving to under repair group, keep in schedule
			log.debug(f"MainItem({main_id}) moved to Under Repair Group, keeping in schedule")
			return jsonify({'message': 'OK'}), 200

		# moving to another schedule, delete
		log.debug(f"MainItem({main_id}) moved from repair group({old_group_id})")
		user = users.User(repair_group_id=old_group_id)
		motion = MotionClient(user)
		motion.delete_task(main.motion_task_id.value)
		main.motion_task_id = None
		main.motion_scheduling_status = "Not In Repair Schedule"
		scheduling.schedule_update(old_group_id)

	if new_group_id in repair_group_ids:
		# repair has been moved a repairer's group, add motion task to new repairer schedule
		log.debug(f"MainItem({main_id}) moved to repair group({new_group_id})")
		user = users.User(repair_group_id=new_group_id)
		motion = MotionClient(user)
		try:
			if main.products_connect.value:
				prod_data = monday.api.get_api_items(main.products_connect.value)
				products = [items.ProductItem(p['id'], p) for p in prod_data]
				duration = max([p.required_minutes for p in products]) or 60
			else:
				duration = 60
			task = motion.create_task(
				name=main.name,
				deadline=main.hard_deadline.value,
				description=main.description.value,
				labels=['Repair'],
				duration=duration
			)
			log.debug(f"Created Motion Task({task['id']}) for MainItem({main_id})")
		except (scheduling.MissingDeadlineInMonday, AttributeError):
			log.debug(f"MainItem({main_id}) missing deadline, not creating motion task")
			main.commit()
			return jsonify({'message': 'Missing Deadline'}), 200

		main.motion_task_id = task['id']
		main.motion_scheduling_status = 'Awaiting Sync'
		scheduling.schedule_update(new_group_id)

	main.commit()
	return jsonify({'message': 'OK'}), 200


@scheduling_bp.route("/client-side-deadline-adjusted", methods=["POST"])
@monday_challenge
def handle_client_side_deadline_adjustment():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']
	group_id = data['groupId']

	all_users = [users.User(_['name']) for _ in users.USER_DATA]
	repair_group_ids = [
		user.repair_group_id for user in all_users if user.name in ('safan', 'andres')
	]
	if group_id not in repair_group_ids:
		log.debug("CS Deadline Adjusted within non-repair group, do nothing")
		return jsonify({'message': 'Not a repair group'}), 200

	user = users.User(repair_group_id=group_id)
	motion = MotionClient(user)
	item = monday.api.get_api_items([data['pulseId']])[0]
	main = items.MainItem(item['id'], item)

	if main.motion_task_id.value:
		if not main.hard_deadline.value:
			log.debug(f"{main.name} missing deadline, deleting task")
			motion.delete_task(main.motion_task_id.value)
			main.motion_task_id = None
			main.motion_scheduling_status = "No Deadline"
			main.commit()
			scheduling.schedule_update(group_id)
			return jsonify({'message': 'Missing Deadline'}), 200

		else:
			log.debug(f"Updating Motion Task({main.motion_task_id}) deadline for {main.hard_deadline}")
			try:
				motion.update_task(
					task_id=main.motion_task_id.value,
					deadline=main.hard_deadline.value
				)
				log.debug(f"Updated Motion Task({main.motion_task_id}) deadline for MainItem({main.id})")
			except MotionError:
				log.debug(f"Motion Task({main.motion_task_id}) not found, creating instead")
				if main.products_connect.value:
					prod_data = monday.api.get_api_items(main.products_connect.value)
					duration = max(
						[items.ProductItem(p['id'], p).required_minutes.value for p in prod_data]
					)
				else:
					duration = 60
				task = motion.create_task(
					name=main.name,
					deadline=main.hard_deadline.value,
					description=main.description.value,
					labels=['Repair'],
					duration=duration
				)
				main.motion_task_id = task['id']
			scheduling.schedule_update(group_id)
			main.motion_scheduling_status = 'Awaiting Sync'
			main.commit()
			return jsonify({'message': 'OK'}), 200

	else:
		log.debug(f"MainItem({main.id}) missing motion task, Cannot update Task. Creating instead")
		try:
			task = motion.create_task(
				name=main.name,
				deadline=main.hard_deadline.value,
				description=main.description.value,
				labels=['Repair']
			)
			log.debug(f"Created Motion Task({task['id']}) for MainItem({main.id})")
			main.motion_task_id = task['id']
			main.motion_scheduling_status = 'Awaiting Sync'
			main.commit()
			scheduling.schedule_update(group_id)
		except (scheduling.MissingDeadlineInMonday, AttributeError):
			log.debug(f"MainItem({main.id}) missing deadline, not creating motion task")
			main.motion_scheduling_status = "No Deadline"
			main.commit()
			return jsonify({'message': 'Missing Deadline'}), 200

	return jsonify({'message': 'Added Motion Task'}), 200
