from typeform import Typeform

import config

conf = config.get_config()

class TypeformClient:
	def __init__(self, api_key):
		self.client = Typeform(api_key)

	def get_responses(
			self,
			form_id,
			since=None,
			until=None,
			after=None,
			before=None,
			completed=None,
			sort=None,
			query=None,
			fields=None
	):
		return self.client.responses.list(
			uid=form_id,
			since=since,
			until=until,
			after=after,
			before=before,
			completed=completed,
			sort=sort,
			query=query,
			fields=fields
		)


conn = TypeformClient(conf.TYPEFORM_API_KEY)
