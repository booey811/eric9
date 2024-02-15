from ...services import typeform, monday
from ...services.monday.items.misc import TypeFormWalkInResponseItem


def sync_typeform_response_with_monday(response_item_id):
	i = TypeFormWalkInResponseItem(response_item_id)
	i.sync_typeform_data()
	return i
