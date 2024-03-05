import logging
from dateutil import parser
import datetime

from ...services import monday, gcal
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


def end_session(main_id, timestamp: str, ending_status, post_update: str = ''):
	active_session = get_active_session(main_id)

	if not active_session:
		notify_admins_of_error(f"No active session found for {main_id}, cannot end session")
		return False

	if isinstance(timestamp, datetime.datetime):
		timestamp = timestamp.strftime("%c")

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


def map_session_to_gcal(session_item_id):
	session = monday.items.misc.RepairSessionItem(session_item_id)
	try:
		user = users.User(monday_id=session.technician.value[0])
	except IndexError:
		notify_admins_of_error(f"Session {session} has no technician, cannot plot to gcal")
		session.gcal_plot_status = "No Technician"
		session.commit()
		return False

	sessions_cal_id = user.gcal_sessions_id
	start = session.start_time.value
	end = session.end_time.value

	if not end:
		notify_admins_of_error(f"Session {session} has no end time, cannot plot to gcal")
		session.gcal_plot_status = "No End Time"
		session.commit()
		return False

	if not start:
		notify_admins_of_error(f"Session {session} has no start time, cannot plot to gcal")
		session.gcal_plot_status = "No Start Time"
		session.commit()
		return False

	if session.gcal_event_id.value:
		# session is already mapped to a gcal event, edit the event
		try:
			event = [
				e for e in gcal.helpers.get_events_list(cal_id=sessions_cal_id) if
				e['id'] == session.gcal_event_id.value
			][0]
			return gcal.helpers.edit_event(
				cal_id=sessions_cal_id,
				event_obj=event,
				new_start=start,
				new_end=end
			)

		except IndexError:
			notify_admins_of_error(
				f"Session {session} has a gcal event id ({session.gcal_event_id.value}), but no event found in gcal")
			# event not found, create a new one (call a deletion just in case)
			session.gcal_event_id = ''
			try:
				gcal.helpers.delete_event(sessions_cal_id, session.gcal_event_id.value)
			except Exception as e:
				notify_admins_of_error(f"Error deleting event: {str(e)}")

	main_item = monday.items.MainItem(session.main_board_id.value)
	try:
		device = monday.items.DeviceItem(main_item.device_id)
		device_name = device.name
	except Exception as e:
		notify_admins_of_error(f"Could not get device: {str(e)}")
		device_name = 'Unknown Device'

	event_name = f"{main_item.name} ({device_name})"
	description = ''
	for prod in main_item.products:
		description += f"{prod.name}\n"

	event = gcal.helpers.add_to_gcal(
		event_name=event_name,
		calendar_id=sessions_cal_id,
		start_time=start,
		end_time=end,
		description=description,
		properties={
			'session_id': session.id
		}
	)

	session.gcal_event_id = event['id']
	session.gcal_plot_status = 'Complete'

	session.commit()

	return event
