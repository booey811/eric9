import logging
import requests
import json
import os

from zenpy.lib.api_objects import User
from zenpy.lib.exception import APIException

from .client import client
from ...errors import EricError

log = logging.getLogger('eric')


def search_zendesk(query, search_type="user"):
	log.debug(f"Searching Zendesk for {query} of type {search_type}")
	if search_type == 'user':
		results = client.search(user=query)
	else:
		results = client.search(str(query), type=search_type)

	log.debug(f"Zendesk search results: {len(results)}")

	return results


def create_user(name, email, phone):
	log.debug(f"Creating Zendesk user: {name}, {email}, {phone}")
	user_obj = User(
		name=name,
		email=email,
		phone=phone
	)
	new_user = client.users.create(user_obj)
	return new_user


def create_ticket_field_option(ticket_field_id, option_name, option_tag):
	"""

	creates a new ticket field option, assigned to the tag provided, in the relevant custom field

	:param ticket_field_id: ID of the custom field to edit
	:type ticket_field_id: int
	:param option_name: title of the option to be shown to users
	:type option_name: str
	:param option_tag: tag that will be used to control which option is selected
	:type option_tag:
	"""

	import base64

	def _encode_auth():
		plain_str = f"admin@icorrect.co.uk/token:{os.getenv('ZENDESK')}"
		encoded_bytes = base64.b64encode(plain_str.encode("utf-8"))
		encoded_string = encoded_bytes.decode()
		return encoded_string

	HEADERS = {
		"Content-Type": "application/json",
		"Authorization": f"Basic {_encode_auth()}"
	}

	url = f"https://icorrect.zendesk.com/api/v2/ticket_fields/{ticket_field_id}/options"

	data = {
		'custom_field_option': {
			"name": option_name,
			"value": option_tag,
		}
	}

	response = requests.request(
		"POST",
		url,
		headers=HEADERS,
		data=json.dumps(data)
	)

	return response