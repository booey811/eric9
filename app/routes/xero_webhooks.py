"""contains flask routes for listening to Xero webhooks"""
import logging
import os
import hmac
import hashlib
import base64

from flask import Blueprint, request

from ..cache import rq
from .. import tasks

log = logging.getLogger('eric')

xero_bp = Blueprint('xero', __name__, url_prefix="/xero")


@xero_bp.route("/invoice-updated", methods=["POST"])
def process_invoice_update():
	"""Process an invoice update from Xero
	EXAMPLE PAYLOAD:
	{
	"events": [
	{
		"resourceUrl": "https://api.xero.com/api.xro/2.0/Contacts/717f2bfc-c6d4-41fd-b238-3f2f0c0cf777",
		"resourceId": "717f2bfc-c6d4-41fd-b238-3f2f0c0cf777",
		"eventDateUtc": "2017-06-21T01:15:39.902",
		"eventType": "Update",
		"eventCategory": "INVOICE",
		"tenantId": "c2cc9b6e-9458-4c7d-93cc-f02b81b0594f",
		"tenantType": "ORGANISATION"
	},
   ],
   "lastEventSequence": 1,
   "firstEventSequence": 1,
   "entropy": "S0m3r4Nd0mt3xt"
}
	"""

	# Your webhook signing key
	webhook_key = os.environ.get('XERO_WEBHOOK_KEY')

	# Extract the signature from the headers
	signature_header = request.headers.get('X-Xero-Signature')

	# Get the raw body of the request
	payload = request.get_data()

	# Hash the payload using HMACSHA256 with your webhook signing key
	hashed_payload = hmac.new(webhook_key.encode(), payload, hashlib.sha256)

	# Base64 encode the hashed payload
	encoded_hashed_payload = base64.b64encode(hashed_payload.digest()).decode()

	# Compare the base64 encoded hashed payload with the signature from the headers
	if encoded_hashed_payload == signature_header:
		# The payload is valid
		log.debug("Received Xero Invoice Update")
		log.debug(request.get_json())
		rq.q_high.enqueue(
			tasks.monday.sales.notify_of_xero_invoice_payment,
			request.get_json()['events'][0]['resourceId']
		)
		return "OK", 200
	else:
		# The payload is not valid
		return "Invalid payload", 401
