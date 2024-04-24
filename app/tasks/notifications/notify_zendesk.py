import datetime

from zenpy.lib.api_objects import Comment, CustomField

import config
from ...services.monday import items, api
from ..sync_platform import sync_to_zendesk
from ...services import zendesk
from ...utilities import notify_admins_of_error
from ...cache import rq

conf = config.get_config()


def send_macro(main_item_id, second_attempt=False):
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
		def determine_password_state():
			if main_item.main_status.value == 'Password Req':
				# password requested
				current_pc = main_item.passcode.value
				if current_pc:
					if current_pc.lower() == 'will not provide':
						# no email sent, client refuses
						return False
					elif current_pc.lower() == 'n/a':
						# client has advised of no password, but the device requests one
						pw_macro = 360049361977
					else:
						# client has provided password, but this is incorrect
						pw_macro = 24020282847249
				else:
					# no password provided, we must get one
					pw_macro = 24020315030929

				m_e = zendesk.client.tickets.show_macro_effect(ticket, pw_macro)
				res = zendesk.client.tickets.update(m_e.ticket).ticket
				return True

			else:
				return False

		t = determine_password_state()
		if t:
			return t

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

			if main_item.main_status.value in ('Booking Confirmed', 'Courier Booked'):
				try:
					date_custom_field = [cf for cf in ticket.fields if cf['id'] == 10885002669585][0]
				except (TypeError, AttributeError):
					date_custom_field = [cf for cf in ticket.fields if int(cf.id) == 10885002669585][0]

				if not date_custom_field['value'] or date_custom_field['value'] == 'as soon as possible':
					date_from_item = main_item.booking_date.value
					if not date_from_item:
						# date not found, waiting for monday to update itself
						if 'courier' in main_item.service.value.lower():
							ds = 'as soon as possible'
						else:
							if not second_attempt:
								ticket.comment = Comment(
									public=False,
									body=f"Macro Requested: {macro_search_term}, but no date found in Monday. Retrying in 5 mins..."
								)
								ticket.status = 'pending'
								zendesk.client.tickets.update(ticket)
								if conf.CONFIG == 'DEVELOPMENT':
									send_macro(main_item_id, second_attempt=True)
									return False
								else:
									rq.q_high.enqueue_in(
										time_delta=datetime.timedelta(minutes=5),
										func=send_macro,
										kwargs={
											'main_item_id': main_item.id,
											'second_attempt': True
										},
									)
									return False
							else:
								body = f"Macro Requested: {macro_search_term}, but no date found in Monday"
								comment = Comment(
									public=False,
									body=body
								)
								ticket.comment = comment
								ticket.status = 'open'
								zendesk.client.tickets.update(ticket)
								return False
					else:
						def set_booking_date():
							from_item = date_from_item
							if not main_item.service.value:
								raise api.exceptions.MondayDataError(
									"Cannot convert Booking Date to string, please select which service the client will be using")
							if 'mail' in main_item.service.value.lower():
								# mail format: on Wednesday 14th February
								result = from_item.strftime("on %A %d %B")
							else:
								# courier & walk-in format: "at 12:30PM on Wednesday 14 February"
								result = from_item.strftime("at %I:%M%p on %A %d %B")

							return result

						ds = set_booking_date()

					ticket.custom_fields.append(
						CustomField(
							id=10885002669585,
							value=ds
						)
					)
					zendesk.client.tickets.update(ticket)

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
