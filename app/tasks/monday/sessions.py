import logging
from dateutil import parser
import datetime

from ...services import monday
from ...utilities import users, notify_admins_of_error
from ...cache.rq import q_low

log = logging.getLogger('eric')


def begin_new_session(main_id: str | int, timestamp: str, monday_user_id):
	# create a new session for the main item
	main = monday.items.MainItem(main_id)
	user = users.User(monday_id=monday_user_id)
	new = monday.items.misc.RepairSessionItem()

	timestamp = parser.parse(timestamp)

	new.main_board_id = str(main_id)
	new.start_time = timestamp
	new.session_status = 'Active'
	new.technician = [int(user.monday_id)]
	new.phase_label = main.repair_phase.value
	new.device_id = str(main.device_id)

	new.create(f"Session for {main}")

	return new


def end_session(main_id, timestamp, ending_status, post_update: str = ''):

	active_session = get_active_session(main_id)
	timestamp = parser.parse(timestamp)

	return update_session(
		session_id=active_session.id,
		session_status="Complete",
		end_time=timestamp,
		ending_status=ending_status,
		post_update=post_update
	)


def update_session(session_id, session_status='', end_time: str = None, ending_status='Unknown', post_update: str = ''):
	"""
	updates a session with the given parameters, allowing an update to be posted if required
	"""
	session = monday.items.misc.RepairSessionItem(session_id)
	end_time = parser.parse(end_time)
	try:
		if session_status:
			session.session_status = session_status
		if end_time:
			session.end_time = end_time
		if ending_status:
			session.ending_status = ending_status
		session.commit()
	except monday.api.exceptions.MondayError as e:
		notify_admins_of_error(f"Error updating session {session_id}: {e}")

	if post_update:
		session.add_update(post_update)

	return session


def get_active_session(main_id: str | int):
	"""
	gets the active session for a given item, ending any duplicate active sessions
	"""
	# get the active session for the main item
	main = monday.items.MainItem(main_id)
	search_session = monday.items.misc.RepairSessionItem(search=True)
	search_results = search_session.search_board_for_items('main_board_id', str(main.id))
	sessions = [monday.items.misc.RepairSessionItem(item['id'], item) for item in search_results]

	if not sessions:
		return None

	sessions = [item for item in sessions if item.session_status.value == 'Active']
	date_ordered_sessions = sorted(sessions, key=lambda x: x.start_time.value)

	# only the most recent session should ever be active, so make sure the rest of the sessions are marked as complete
	supposed_to_be_inactive = date_ordered_sessions[:-1]
	if supposed_to_be_inactive:
		notify_admins_of_error(f"Multiple active sessions found for {main}")
		for session in supposed_to_be_inactive:
			q_low.enqueue(
				update_session,
				kwargs={
					'session_id': session.id,
					'session_status': 'Complete: Bad Data',
					'end_time': datetime.datetime.now().strftime("%c"),
					'ending_status': 'Unknown',
					'post_update': "Session marked as 'Complete: Bad Data' because of duplicate active sessions"
				}
			)

	if sessions[-1].session_status.value == 'Active':
		active_session = sessions[-1]
		log.debug(f"Got Active Session: {active_session}")
	else:
		active_session = None
		log.debug(f"No Active Session Found for {main}")

	return active_session