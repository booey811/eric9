import os
import base64
import requests
import json

from ...cache import get_redis_connection
from ...utilities import notify_admins_of_error
from ...errors import EricError

_BASE_URL = "https://api.xero.com/api.xro"


def with_retries(func):
	def wrapper(*args, **kwargs):
		try:
			# Try to call the function with the current access token
			return func(*args, **kwargs)
		except XeroAuthError:
			# If authentication failed, refresh the token and try again
			get_redis_connection().delete("xero_access")
			get_access_token()
			return func(*args, **kwargs)

	return wrapper


def get_access_token():
	def encoded_creds():
		string = f"{os.environ['XERO_ID']}:{os.environ['XERO_SECRET']}"
		string_bytes = string.encode("ascii")
		b64_bytes = base64.b64encode(string_bytes)
		b64_string = b64_bytes.decode("ascii")
		return b64_string

	from_cache = get_redis_connection().get("xero_access")
	if from_cache:
		return from_cache.decode()

	url = "https://identity.xero.com/connect/token"

	headers = {
		"Authorization": f"Basic {encoded_creds()}",
	}

	body = {
		"grant_type": "client_credentials",
		"scope": "accounting.transactions accounting.contacts"
	}

	response = requests.request(url=url, method="POST", headers=headers, data=body)
	if response.status_code == 200:
		info = response.json()
		get_redis_connection().set(name="xero_access", value=info["access_token"], ex=info["expires_in"] - 10)
		return info["access_token"]
	else:
		notify_admins_of_error(f"Xero Authorisation Returned non-200 Response: {response.text}")
		raise Exception(f"Xero Authorisation Returned non-200 Response: {response.text}")


def get_headers():
	return {
		"Authorization": f"Bearer {get_access_token()}",
		"Accept": "application/json"
	}


@with_retries
def get_contact(contact_id):
	"""returns list of contacts (usually containing one item)"""
	url = _BASE_URL + f"/2.0/Contacts/{contact_id}"
	result = requests.get(url, headers=get_headers())

	if result.status_code == 200:
		return json.loads(result.text)["Contacts"]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def get_contact_by_email(email):
	"""returns list of contacts filtered by email"""
	url = _BASE_URL + "/2.0/Contacts"
	params = {"where": f'EmailAddress=="{email}"'}
	result = requests.get(url, headers=get_headers(), params=params)

	if result.status_code == 200:
		return json.loads(result.text)["Contacts"]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def get_invoices_for_contact_id(contact_id=None, filter_status=None):
	""""returns list of invoices"""
	url = _BASE_URL + f"/2.0/Invoices"
	body = {}
	if contact_id:
		body = {"ContactIDs": contact_id}
	if filter_status:
		body['Statuses'] = filter_status

	if body:
		result = requests.get(url=url, headers=get_headers(), params=body)
	else:
		result = requests.get(url=url, headers=get_headers())

	if result.status_code == 200:
		return json.loads(result.text)['Invoices']
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def get_invoice_by_id(invoice_id):
	url = _BASE_URL + f"/2.0/Invoices/{invoice_id}"
	result = requests.get(url=url, headers=get_headers())
	if result.status_code == 200:
		return json.loads(result.text)['Invoices'][0]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def create_invoice(contact_id, issue_date, due_date, line_items, reference, line_amount_types="Inclusive"):
	"""Create an invoice for a contact with the given line items."""
	url = _BASE_URL + "/2.0/Invoices"

	# Prepare the invoice data
	invoice_data = {
		"Type": "ACCREC",
		"Contact": {
			"ContactID": contact_id
		},
		"Date": issue_date.isoformat(),
		"DueDate": due_date.isoformat(),
		"LineItems": line_items,
		"Reference": reference,
		"LineAmountTypes": line_amount_types
	}

	# Make the API request
	result = requests.put(url, headers=get_headers(), json={"Invoices": [invoice_data]})

	# Check the response
	if result.status_code == 200:
		return json.loads(result.text)["Invoices"][0]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def create_contact(name, email, street_address=None, postal_code=None):
	"""Create a new contact in Xero."""
	url = _BASE_URL + "/2.0/Contacts"

	# Prepare the contact data
	contact_data = {
		"Name": name,
		"EmailAddress": email,
	}

	address = {}

	if street_address:
		address["AddressLine1"] = street_address
	if postal_code:
		address["PostalCode"] = postal_code

	if address:
		contact_data["Addresses"] = [address]

	# Make the API request
	result = requests.put(url, headers=get_headers(), json={"Contacts": [contact_data]})

	# Check the response
	if result.status_code == 200:
		return json.loads(result.text)["Contacts"][0]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def update_invoice(invoice_dict):
	url = _BASE_URL + f"/2.0/Invoices"
	body = invoice_dict

	result = requests.post(url=url, headers=get_headers(), json=body)
	if result.status_code == 200:
		return json.loads(result.text)['Invoices'][0]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def get_quotes(contact_id, status=''):
	url = _BASE_URL + f"/2.0/Quotes"
	params = {"ContactID": contact_id}

	if status:
		params['Status'] = status

	result = requests.get(url=url, headers=get_headers(), params=params)
	if result.status_code == 200:
		return json.loads(result.text)['Quotes']
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)


@with_retries
def save_quote(quote_dict):
	url = _BASE_URL + f"/2.0/Quotes"
	body = quote_dict

	result = requests.post(url=url, headers=get_headers(), json=body)
	if result.status_code == 200:
		return json.loads(result.text)['Quotes'][0]
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		print(result.text)
		raise XeroResponseError(result)


def make_line_item(description, quantity, unit_amount, account_code=203, tax_type="OUTPUT2", line_amount_types="Exclusive"):
	return {
		"Description": description,
		"Quantity": quantity,
		"UnitAmount": unit_amount,
		"AccountCode": account_code,
		"TaxType": tax_type,
		"LineAmountTypes": line_amount_types,
	}


def get_payment_url(invoice_id):
	url = _BASE_URL + f"/2.0/Invoices/{invoice_id}/OnlineInvoice"
	result = requests.get(url=url, headers=get_headers())
	if result.status_code == 200:
		return json.loads(result.text)['OnlineInvoices'][0]['OnlineInvoiceUrl']
	elif result.status_code == 401:
		raise XeroAuthError
	else:
		raise XeroResponseError(result)

class XeroError(EricError):
	def __init__(self, message):
		super().__init__(message)


class XeroAuthError(XeroError):
	def __init__(self):
		super().__init__("Xero Authorisation Failed")


class XeroResponseError(XeroError):
	def __init__(self, response_object):
		self.response = response_object
		super().__init__(f"XeroResponseError: {response_object.text}")
