from zenpy.lib.api_objects import Comment

from ...services.monday import items
from ..sync_platform import sync_to_zendesk
from ...services import zendesk
from ...utilities import notify_admins_of_error


def send_macro(main_item_id):
	try:
		main_item = items.MainItem(main_item_id).load_from_api()
	except Exception as e:
		raise e

	try:
		ticket = zendesk.client.tickets(id=int(main_item.ticket_id.value))
	except Exception as e:
		raise e

	try:
		sync_to_zendesk(main_item.id, ticket.id)
	except Exception as e:
		raise e

	try:
		search_item = items.misc.NotificationMappingItem(search=True)

		macro_search_term = f"{main_item.main_status.value}-{main_item.client.value}-{main_item.service.value}"
		if 'stuart' in main_item.service.value.lower() or 'gophr' in main_item.service.value.lower():
			macro_search_term = f"{main_item.main_status.value}-{main_item.client.value}-Courier"
		results = search_item.search_board_for_items('macro_search_term', macro_search_term)

		if not results:
			# body = f"Could not find macro for {macro_search_term}, no macro sent"
			# # macro search has failed
			# comment = Comment(
			# 	public=False,
			# 	body=body
			# )
			# ticket.comment = comment
			# zendesk.client.tickets.update(ticket)
			return False
		elif len(results) > 1:
			body = f"Too Many Macros ({len(results)}) Found for {macro_search_term}, no macro sent"
			# macro search has failed
			comment = Comment(
				public=False,
				body=body
			)
			ticket.comment = comment
			zendesk.client.tickets.update(ticket)
			return False
		else:
			notifier_item = items.misc.NotificationMappingItem(results[0]['id'], results[0])
			if main_item.notifications_status.value != 'ON':
				body = f"Macro Requested: {macro_search_term}, but notifications are OFF for this item"
				comment = Comment(
					public=False,
					body=body
				)
				ticket.comment = comment
				zendesk.client.tickets.update(ticket)
				return False

			notification_tag = notifier_item.name.replace(" ", "_").lower() + "_sent"

			if notification_tag in ticket.tags:
				body = (f"Macro Requested: {macro_search_term}, but has already been sent. To re-send this "
						f"notification, please remove the tag '{notification_tag}' from the ticket")
				comment = Comment(
					public=False,
					body=body
				)
				ticket.comment = comment
				zendesk.client.tickets.update(ticket)
				return False

			macro_id = notifier_item.macro_id.value
			macro_effect = zendesk.client.tickets.show_macro_effect(ticket, macro_id)
			macro_effect.ticket.tags.extend([notification_tag])
			ticket = zendesk.client.tickets.update(macro_effect.ticket).ticket
			return ticket

	except Exception as e:
		message = f"Error sending macro for {main_item}: {e}"
		main_item.add_update(message, main_item.notes_thread_id.value)
		ticket.comment = Comment(public=False, body=message)
		zendesk.client.tickets.update(ticket)
		notify_admins_of_error(message)
		raise e
