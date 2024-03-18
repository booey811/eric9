import datetime
import logging
import json

from flask import Blueprint, request, jsonify

from ...services.monday import monday_challenge, items
from ...services import monday
from ...utilities import notify_admins_of_error
from ...errors import EricError
from ...cache.rq import q_low, q_high
from ...tasks.monday import web_bookings, sessions, misc
from ...tasks import notifications, stuart, monday

log = logging.getLogger('eric')

main_board_bp = Blueprint('main_board', __name__, url_prefix="/main-board")


@main_board_bp.route("/tech-status", methods=["POST"])
@monday_challenge
def handle_tech_status_adjustment():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	repair_paused_status_labels = (
		'No/Incorrect Password',
		'Parts Issue',
		'Stuck with Repair',
		'Jump to Other Repair',
		'Battery Testing',
	)

	new_label = data['value']['label']['text']
	log.debug(f"Tech Status Adjustment: {new_label}")

	log.debug('Dealing with session records....')

	if new_label == 'Active':
		# start new session

		q_high.enqueue(
			sessions.begin_new_session,
			kwargs={
				'main_id': data['pulseId'],
				'timestamp': datetime.datetime.now().strftime("%c"),
				'monday_user_id': data['userId']
			}
		)

	else:
		# end current and any other active sessions
		q_low.enqueue(
			sessions.end_session,
			kwargs={
				'main_id': data['pulseId'],
				'timestamp': datetime.datetime.now().strftime("%c"),
				'ending_status': new_label
			}
		)

	log.debug('Dealing with phases.....')

	main_id = data['pulseId']
	main = items.MainItem(main_id).load_from_api()

	def get_next_phase_entity():
		# get_phase_model, then look at line items and match self.phase_status to line item mainboard_repair_status
		phase_model = main.get_phase_model()
		lines = phase_model.phase_lines
		log.debug(f"Got {len(lines)} phase lines:")
		for line in lines:
			log.debug(str(line))
		for i, line in enumerate(lines):
			phase_entity = line.get_phase_entity_item()
			log.debug(str(phase_entity))
			if phase_entity.main_board_phase_label.value == main.repair_phase.value:
				# Check if there is a next item
				if i + 1 < len(lines):
					next_line = lines[i + 1]
					return next_line.get_phase_entity_item()
				else:
					# There is no next item, handle accordingly
					return None

	if new_label == 'Complete':
		log.debug(f"Phase completed, moving to next phase")
		next_phase = get_next_phase_entity()
		if not next_phase:
			# no more phases, repair has been completed
			main.repair_phase = "Repaired"
		else:
			main.repair_phase = next_phase.main_board_phase_label.value
			main.phase_status = "Not Started"

		main.commit()

	elif new_label in repair_paused_status_labels:
		log.warning(f"Repair Paused: {new_label}")
		notify_admins_of_error(f"{str(main)} paused with status: {new_label}. Actions will neeed to be taken")

	elif new_label == 'Not Started':
		log.debug('Not Started: Do Nothing')
		notify_admins_of_error(f"{str(main)} has been reset to Not Started. This is likely a system change.")

	elif new_label == 'Active':
		log.warning("Not Yet Developed")
		notify_admins_of_error("Tech Status Adjustment: Active. A technician has started repairing a phase")

	else:
		raise EricError(f"Unknown Tech Status: {new_label}")

	return jsonify({'message': 'OK'}), 200


@main_board_bp.route('/add-web-booking', methods=["POST"])
@monday_challenge
def handle_web_booking():
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	web_booking_id = data['pulseId']
	log.debug(f"Handling Web Booking: {web_booking_id}")

	q_low.enqueue(
		web_bookings.transfer_web_booking,
		web_booking_id
	)

	return jsonify({'message': 'OK'}), 200


@main_board_bp.route('/main-status-change', methods=["POST"])
@monday_challenge
def handle_main_status_adjustment():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	log.debug(data)

	q_high.enqueue(
		notifications.notify_zendesk.send_macro,
		data['pulseId']
	)

	under_repair_statuses = [
		"Under Repair",
		"Diagnostics",
	]

	new_label = data['value']['label']['text']

	if new_label in under_repair_statuses:
		q_high.enqueue(
			sessions.begin_new_session,
			kwargs={
				'main_id': data['pulseId'],
				'timestamp': datetime.datetime.now().strftime("%c"),
				'monday_user_id': data['userId']
			}
		)
	else:
		q_low.enqueue(
			sessions.end_session,
			kwargs={
				'main_id': data['pulseId'],
				'timestamp': datetime.datetime.now().strftime("%c"),
				'ending_status': new_label
			}
		)

	if new_label == 'Repaired':
		q_low.enqueue(
			monday.stock_control.update_stock_checkouts,
			kwargs={
				"main_id": data['pulseId'],
				"create_sc_item": True
			}
		)

	return jsonify({'message': 'OK'}), 200


@main_board_bp.route('/book-collection', methods=["POST"])
@monday_challenge
def book_courier_collection():
	log.debug('Booking Courier Collection')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_high.enqueue(
		stuart.book_courier(data['pulseId'], 'incoming')
	)
	return jsonify({'message': 'OK'}), 200


@main_board_bp.route('/book-return', methods=["POST"])
@monday_challenge
def book_courier_return():
	log.debug('Booking Courier Return')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_high.enqueue(
		stuart.book_courier(data['pulseId'], 'outgoing')
	)
	return jsonify({'message': 'OK'}), 200


@main_board_bp.route('/repair-parts-adjustment')
@monday_challenge
def handle_changing_of_parts_used_data():
	log.debug('Handling adjustment in parts used columns')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_low.enqueue(
		monday.stock_control.update_stock_checkouts,
		kwargs={
			"main_id": data['pulseID'],
			"create_sc_item": False
		}
	)

	return jsonify({'status': 'ok'}), 200


@main_board_bp.route("/handle-imei-change")
@monday_challenge
def handle_imei_change():
	log.debug('Booking Courier Return')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	q_high.enqueue(
		misc.handle_imei_change,
		data['pulseId']
	)

	return jsonify({'message': 'OK'}), 200
