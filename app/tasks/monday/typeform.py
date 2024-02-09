from ...services import typeform, monday
from ...services.monday.items.misc import TypeFormWalkInResponseItem


def sync_typeform_response_with_monday(response_item_id):
	i = TypeFormWalkInResponseItem(response_item_id, monday.api.get_api_items([response_item_id])[0])
	i.sync_typeform_data()
	return i
