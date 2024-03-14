import os
import requests
import json
import logging

from . import client, helpers

logger = logging.getLogger()


class StuartClient:

	def __init__(self):
		pass

		# self.headers = {
		# }
		#
		# if os.environ["STUART_PROD"] == 'sand':
		# 	self._id = os.environ["STUART_ID_SAND"]
		# 	self._secret = os.environ["STUART_SECRET_SAND"]
		# 	self._base_url = "https://api.sandbox.stuart.com"
		# 	self._token = None
		# 	self._oauth()
		# elif os.environ["ENV"] == 'devlocal':
		# 	self._id = os.environ["STUART_ID_SAND"]
		# 	self._secret = os.environ["STUART_SECRET_SAND"]
		# 	self._base_url = "https://api.sandbox.stuart.com"
		# 	self._token = None
		# 	self._oauth()
		# elif os.environ["ENV"] == 'production':
		# 	self._id = os.environ["STUART_ID_PROD"]
		# 	self._secret = os.environ["STUART_SECRET_PROD"]
		# 	self._base_url = "https://api.stuart.com"
		# 	self._oauth()
		# 	# self._token = memcache.get("stuart_token")
		# 	self.headers = {
		# 		"Authorization": f"Bearer {self._token}"
		# 	}
		# else:
		# 	raise Exception(f"Invalid Environment: {os.environ['ENV']}")

	def _test_auth(self):
		url = self._base_url + "/v2/areas/london?type=picking"
		result = requests.get(url, headers=self.headers)
		if result.status_code == 200:
			return True
		else:
			self._oauth()

	def _oauth(self):
		url = self._base_url + "/oauth/token"
		headers = {'Content-Type': "application/x-www-form-urlencoded"}
		data = {
			"client_id": self._id,
			"client_secret": self._secret,
			"grant_type": "client_credentials",
			'scope': "api"
		}
		result = requests.post(url, data=data, headers=headers)
		if result.status_code == 200:
			self._token = json.loads(result.text)['access_token']
			if os.environ["ENV"] == 'production':
				memcache.set("stuart_token", self._token)
			self.headers["Authorization"] = f"Bearer {self._token}"
			return True
		else:
			raise Exception(f"Stuart Auth Error ({result.status_code}): {result.text}")

	def validate_address(self, street, postcode, phone=''):
		url = self._base_url + f"/v2/addresses/validate"
		headers = {
			'Content-Type': "application/x-www-form-urlencoded",
			"Authorization": f"Bearer {self._token}"
		}

		add_str = f"{street} {postcode}"

		data = {
			"address": add_str,
			"type": "picking",
		}
		if phone:
			data['phone'] = phone
		else:
			data['phone'] = '02070998517'

		logger.info(f"Validating {str(data)}")
		result = requests.get(url, headers=headers, data=data)

		if result.status_code == 200:
			return add_str
		elif result.status_code == 422:
			text = json.loads(result.text)
			raise StuartValidationError(text['error'])
		else:
			try:
				message = json.loads(result.text)
			except json.decoder.JSONDecodeError as e:
				message = result.text
			raise StuartValidationError(f"Unknown Stuart Error ({result.status_code}): {message}")

	def _prepare_job_data(self, first_name, last_name, phone, email, address_string, notes, collect_or_deliver,
	                      company):

		if collect_or_deliver == 'collect':
			collection = {
				"address": address_string,
				"comment": notes,
				"contact": {
					"firstname": first_name,
					"lastname": last_name,
					"phone": phone,
					"email": email,
					"company": company
				},
				"access_codes": [
					{
						"code": "your_access_code_1",
						"type": "text",
						"title": "access code title",
						"instructions": "please put your instructions here"
					}
				]
			}
			delivery = {
				"package_type": "medium",
				"package_description": "package",
				"client_reference": "",
				"address": "iCorrect, 12 Margaret Street, W1W 8JQ",
				# "end_customer_time_window_start": "2021-12-12T11:00:00.000+02:00",
				# "end_customer_time_window_end": "2021-12-12T13:00:00.000+02:00",
				"contact": {
					"firstname": "Gabriel",
					"lastname": "Barr",
					"phone": "+442070998517",
					"email": "admin@panrix.co.uk",
					"company": "iCorrect"
				},
				"access_codes": [
					{
						"code": "your_access_code_2",
						"type": "text",
						"title": "access code title",
						"instructions": "please put your instructions here"
					}
				]
			}

		elif collect_or_deliver == 'deliver':
			delivery = {
				"address": address_string,
				"comment": notes,
				"contact": {
					"firstname": first_name,
					"lastname": last_name,
					"phone": phone,
					"email": email,
					"company": company
				},
				# "access_codes": [
				# 	{
				# 		"code": "your_access_code_1",
				# 		"type": "text",
				# 		"title": "access code title",
				# 		"instructions": "please put your instructions here"
				# 	}
				# ]
			}
			collection = {
				"package_type": "medium",
				"package_description": "package",
				"client_reference": "[your_client_ref]",
				"address": "iCorrect, 12 Margaret Street, W1W 8JQ",
				# "end_customer_time_window_start": "2021-12-12T11:00:00.000+02:00",
				# "end_customer_time_window_end": "2021-12-12T13:00:00.000+02:00",
				"contact": {
					"firstname": "Gabriel",
					"lastname": "Barr",
					"phone": "+442070998517",
					"email": "admin@panrix.co.uk",
					"company": "iCorrect"
				},
				# "access_codes": [
				# 	{
				# 		"code": "your_access_code_2",
				# 		"type": "text",
				# 		"title": "access code title",
				# 		"instructions": "please put your instructions here"
				# 	}
				# ]
			}
		else:
			raise Exception(f"Invalid Command for Collection/Delivery: {collect_or_deliver}")

		data = {
			"job": {
				"pickups": [collection],
				"dropoffs": [delivery]
			}
		}

		return data

	def validate_job(self, first_name, last_name, phone, email, address_string, notes, collect_or_deliver,
	                 company=''):

		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._token}"
		}

		data = self._prepare_job_data(
			first_name=first_name,
			last_name=last_name,
			phone=phone,
			email=email,
			address_string=address_string,
			notes=notes,
			collect_or_deliver=collect_or_deliver,
			company=company
		)

		url = self._base_url + "/v2/jobs/validate"

		result = requests.post(url, headers=headers, data=json.dumps(data))

		if result.status_code == 200:
			return result
		else:
			try:
				message = json.loads(result.text)
			except json.decoder.JSONDecodeError as e:
				message = result.text
			raise StuartValidationError(f"Unknown Stuart Error ({result.status_code}): {message}")

	def new_validate(self, job_data: dict):
		url = self._base_url + "/v2/jobs/validate"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._token}"
		}
		payload = json.dumps(job_data)
		result = requests.post(url, headers=headers, data=payload)
		if result.status_code == 401:
			self._oauth()
			result = requests.post(url, headers=headers, data=payload)
		return result

	def get_price(self, job_data: dict):

		url = self._base_url + "/v2/jobs/pricing"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._token}"
		}
		payload = json.dumps(job_data)
		result = requests.post(url, headers=headers, data=payload)
		if result.status_code == 401:
			self._oauth()
			result = requests.post(url, headers=headers, data=payload)
		return result

	def create_job(self, job_data: dict):

		url = self._base_url + "/v2/jobs"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._token}"
		}
		payload = json.dumps(job_data)
		result = requests.post(url, headers=headers, data=payload)
		if result.status_code == 401:
			self._oauth()
			result = requests.post(url, headers=headers, data=payload)
		return result


stuart = StuartClient()

if __name__ == '__main__':
	pass
