import logging
import json

from flask import Blueprint, request, jsonify

from ...services.monday import monday_challenge
from ...utilities import notify_admins_of_error
from ...models import MainModel
from ...errors import EricError

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
		# in the future, this will create a repair session record and begin timing
		log.warning(f"Not Yet Developed")
		notify_admins_of_error("Tech Status Adjustment: Active is not yet developed. This will begin recording a session.")
	else:
		# in the future, this will end the repair session and record the time
		log.warning(f"Not Yet Developed")
		notify_admins_of_error(
			f"Tech Status Adjustment: {new_label} is not yet developed\n\nIn future, this will close the current "
			f"session and record the time."
		)

	log.debug('Dealing with phases.....')

	main_id = data['pulseId']
	main = MainModel(main_id)

	if new_label == 'Complete':
		log.debug(f"Phase completed, moving to next phase")
		next_phase = main.get_next_phase()
		if not next_phase:
			# no more phases, repair has been completed
			main.model.repair_phase = "Repaired"
		else:
			main.model.repair_phase = next_phase.phase_entity.main_board_phase_label
			main.model.phase_status = "Not Started"

		main.model.save()

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
