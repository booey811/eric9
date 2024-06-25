# This file contains tasks that are run periodically to track and reconcile web enquiries
import datetime

import pytz


def reconcile_enquiry_conversions(start=datetime.datetime.now() - datetime.timedelta(days=1, hours=1)):
	from app.services import zendesk, monday
	today = datetime.datetime.now()
	r = zendesk.client.search(tags="web_enquiry", created_between=[start, today])
	main_item_field_id = zendesk.custom_fields.FIELDS_DICT['main_item_id']
	count = 1
	start = start.replace(tzinfo=pytz.timezone("Europe/London"))
	for ticket in r:
		print(f"Processing ticket {count}")
		main_item_field = [field for field in ticket.custom_fields if field['id'] == main_item_field_id][0]
		if main_item_field['value']:
			print('found ticket with main item id')
			web_enquiry_search = monday.api.monday_connection.items.fetch_items_by_column_value(
				863729294,
				"zendesk_id",
				value=str(ticket.id)
			)
			if web_enquiry_search.get("error_message"):
				print(f"ERROR ===== {ticket.id}")
				print(web_enquiry_search.get("error_message"))
				continue

			web_enquiry_search = web_enquiry_search['data']['items_page_by_column_values']['items']
			web_enquiries = []
			for item in web_enquiry_search:
				i = monday.items.misc.WebEnquiryItem(item['id'], item)
				i.converted_status = "Added through Zendesk"
				i.commit()
				web_enquiries.append(i)
				print(f"{str(i)} converted through Zendesk")

		email = ticket.requester.email
		search = monday.items.misc.WebBookingItem(search=True).search_board_for_items(
			"email",
			str(email)
		)

		if search:
			web_enquiry_search = monday.api.monday_connection.items.fetch_items_by_column_value(
				863729294,
				"text",
				value=str(email)
			)
			if web_enquiry_search.get("error_message"):
				print(f"ERROR ===== {ticket.id}")
				print(web_enquiry_search.get("error_message"))
				continue

			web_enquiry_search = web_enquiry_search['data']['items_page_by_column_values']['items']
			i = monday.items.misc.WebEnquiryItem(web_enquiry_search[0]['id'], web_enquiry_search[0])
			if i.date_received.value > start:
				i.converted_status = 'Web Booking'
				i.commit()
				print(f"{str(i)} converted through Web Booking")

		count += 1


if __name__ == '__main__':
	reconcile_enquiry_conversions()
