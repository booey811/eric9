import os

from zenpy import Zenpy


client = Zenpy(
	email='admin@icorrect.co.uk',
	token=os.environ["ZENDESK"],
	subdomain="icorrect"
)