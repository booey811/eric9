import os
import json

import googleapiclient.errors
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
	'https://www.googleapis.com/auth/drive',
	'https://www.googleapis.com/auth/calendar',
]


def _get_client():
	js_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
	js = json.loads(js_str)
	js['private_key'] = js['private_key'].replace('\\n', '\n')
	creds = service_account.Credentials.from_service_account_info(
		js,
		scopes=SCOPES
	)

	creds = creds.with_scopes(SCOPES)
	creds = creds.with_subject('gabriel@icorrect.co.uk')

	return build(
		'calendar',
		'v3',
		credentials=creds,
	)


google_client = _get_client()
