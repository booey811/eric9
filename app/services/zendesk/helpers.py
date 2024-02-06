import logging

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


