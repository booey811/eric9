import requests
import json

import config
from .exceptions import StuartAPIError, StuartAuthenticationError, AddressError
from ...cache import get_redis_connection

conf = config.get_config()


def get_auth_header():
	return {
		"Authorization": f"Bearer {get_redis_connection().get('stuart_token').decode()}"
	}


if conf.STUART_ENV == 'production':
	BASE_URL = "https://api.stuart.com"
else:
	BASE_URL = "https://api.sandbox.stuart.com"


def validate_address(address_string, phone=''):
	url = BASE_URL + "/v2/addresses/validate"
	headers = {
		'Content-Type': "application/json",
	}

	headers.update(get_auth_header())

	if not phone:
		phone = '02070998517'

	params = {
		"address": address_string,
		"phone": phone,
		"type": "picking",
	}
	response = send_request(
		url=url,
		method="GET",
		params=params,
		headers=headers
	)

	if response.status_code == 200:
		return json.loads(response.text)
	else:
		raise AddressError(f"Stuart Address Validation Error: {response.text}")


def create_job(job_data):
	url = BASE_URL + "/v2/jobs"
	headers = {
		"Authorization": f"Bearer {get_redis_connection().get('stuart_token')}",
		"Content-Type": "application/json"
	}
	return send_request(
		url=url,
		method="POST",
		data=job_data,
		headers=headers
	)


def send_request(url, method, headers, data=None, params=None):
	"""Send a request to the Stuart API and handle the response, re-authenticating if necessary."""
	response = requests.request(method=method, url=url, data=data, headers=headers, params=params)
	if response.status_code == 200:
		# let it flow through
		pass
	elif response.status_code == 401:
		# Re-authenticate
		authenticate()
		response = requests.request(method=method, url=url, data=data, headers=headers, params=params)
		if response.status_code == 401:
			# If still unauthorized, raise a custom error
			raise StuartAuthenticationError("Re-authentication failed. Please check your credentials.")
	elif response.status_code == 422:
		raise StuartAPIError(f"Stuart 422 Error: {response.text}")
	else:
		raise StuartAPIError(f"Unexpected Stuart API Error ({response.status_code}): {response.text}")
	return response


def authenticate():
	"""Authenticate with the Stuart API and store the token."""
	url = BASE_URL + "/oauth/token"
	headers = {'Content-Type': "application/x-www-form-urlencoded"}
	data = {
		"client_id": conf.STUART_CLIENT_ID,
		"client_secret": conf.STUART_CLIENT_SECRET,
		"grant_type": "client_credentials",
		'scope': "api"
	}
	result = requests.post(url, data=data, headers=headers)
	if result.status_code == 200:
		token = json.loads(result.text)['access_token']
		get_redis_connection().set("stuart_token", token)
	else:
		raise StuartAPIError(f"Stuart Auth Error ({result.status_code}): {result.text}")
	return result
