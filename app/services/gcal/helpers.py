import datetime
import pytz

from .client import google_client as client
from .exceptions import GCalAPIError

EVENT_COLOUR_DATA = {
	'1': {'background': '#a4bdfc', 'foreground': '#1d1d1d'},  # light blue
	'10': {'background': '#51b749', 'foreground': '#1d1d1d'},  # green (walk-in)
	'11': {'background': '#dc2127', 'foreground': '#1d1d1d'},  # red
	'2': {'background': '#7ae7bf', 'foreground': '#1d1d1d'},  # green
	'3': {'background': '#dbadff', 'foreground': '#1d1d1d'},  # purple
	'4': {'background': '#ff887c', 'foreground': '#1d1d1d'},  # pink
	'5': {'background': '#fbd75b', 'foreground': '#1d1d1d'},  # banana (couriers)
	'6': {'background': '#ffb878', 'foreground': '#1d1d1d'},  # nude
	'7': {'background': '#46d6db', 'foreground': '#1d1d1d'},  # teal
	'8': {'background': '#e1e1e1', 'foreground': '#1d1d1d'},  # grey
	'9': {'background': '#5484ed', 'foreground': '#1d1d1d'}  # navy blue
}


def clear_cal(cal_id):
	for event in get_events_list(cal_id):
		client.events().delete(calendarId=cal_id, eventId=event['id']).execute()


def get_events_list(cal_id, prop=None):
	"""
	gets a list of events when given a calendar ID. can also use the prop param to constrain the received events via
	shared properties. weirdly, this should be in the form of a list of strings with 'PropertyName=Value'
	Parameters
	----------
	cal_id : ID of the Gcal to search
	prop (list) : list of strings in form 'PropertyName=Value'

	Returns
	-------

	"""
	page_token = None
	results = []
	while True:
		if prop:
			events = client.events().list(
				calendarId=cal_id,
				pageToken=page_token,
				sharedExtendedProperty=prop).execute()
		else:
			events = client.events().list(calendarId=cal_id, pageToken=page_token).execute()

		for event in events['items']:
			results.append(event)
		page_token = events.get('nextPageToken')
		if not page_token:
			break
	return results


def add_to_gcal(event_name, calendar_id, start_time: datetime.datetime, end_time: datetime.datetime, description='',
				attendees=(), properties=(), colour_id=None):
	data = {
		"summary": str(event_name),
		"start": {
			"dateTime": start_time.astimezone(pytz.timezone('Europe/London')).isoformat(),
		},
		"end": {
			"dateTime": end_time.astimezone(pytz.timezone("Europe/London")).isoformat(),
		},
	}
	if description:
		data["description"] = description
	if attendees:
		data['attendees'] = []
		for email in attendees:
			data['attendees'].append({'email': email})

	if properties:
		data['extendedProperties'] = {}
		data['extendedProperties']['shared'] = {}
	for prop in properties:
		data['extendedProperties']['shared'][prop] = properties[prop]

	if colour_id:
		if str(colour_id) not in EVENT_COLOUR_DATA:
			raise ValueError(f"Invalid Colour ID: {colour_id}")
		data['colorId'] = str(colour_id)

	try:
		result = client.events().insert(calendarId=str(calendar_id), body=data).execute()
		return result
	except Exception as e:
		raise GCalAPIError(str(e))


def edit_event(cal_id, event_obj, new_start: datetime.datetime = None, new_end: datetime.datetime = None):
	if new_start:
		event_obj['start'] = {'dateTime': new_start.astimezone().isoformat()}
	if new_end:
		event_obj['end'] = {'dateTime': new_end.astimezone().isoformat()}

	updated_event = client.events().update(calendarId=cal_id, eventId=event_obj['id'], body=event_obj).execute()
	return updated_event


def delete_event(cal_id, event_id):
	try:
		return client.events().delete(calendarId=cal_id, eventId=event_id).execute()
	except Exception as e:
		raise GCalAPIError(f"Error Updating Event ({event_id}): {str(e)}")
