import os

from woocommerce import API

woo = API(
	url="https://icrtcont.icorrect.co.uk",
	consumer_key=os.environ['WOO_KEY'],
	consumer_secret=os.environ['WOO_SECRET'],
	version="wc/v3"
)

