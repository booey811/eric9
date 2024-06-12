"""contains flask routes for listening to Xero webhooks"""
import logging

from flask import Blueprint, request

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
	log.debug("Received Xero Invoice Update")
	log.debug(request.get_json())

	return "OK", 200
