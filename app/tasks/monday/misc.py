import json

from ...services import monday, sickw
from ...utilities import notify_admins_of_error


def handle_imei_change(main_item_id):
	update = "====!  SICKW DATA CHECK  !====\n"
	main = monday.items.MainItem(main_item_id)
	imei_item = None
	if not main.imeisn.value:
		# no IMEI provided, ignore
		return False
	else:
		# search DB for imei/sn
		results = monday.api.monday_connection.items.fetch_items_by_column_value(
			board_id=5808954740,
			column_id='text',  # imei column
			value=main.imeisn.value
		)
		if len(results['data']['items_page_by_column_values']['items']) == 1:
			# already searched for this IMEI
			api_data = results['data']['items_page_by_column_values']['items'][0]
			imei_item = monday.items.misc.SickWDataItem(api_data['id'], api_data)
		elif results.get('error_message'):
			raise monday.api.exceptions.MondayDataError(f"Error Fetching SickW by IMEI: {results['error_message']}")
		else:
			# not found with IMEI search, try SN
			results = monday.api.monday_connection.items.fetch_items_by_column_value(
				board_id=5808954740,
				column_id='text8',  # serial column
				value=main.imeisn.value
			)
			if len(results['data']['items_page_by_column_values']['items']) == 1:
				# already searched for this SN
				api_data = results['data']['items_page_by_column_values']['items'][0]
				imei_item = monday.items.misc.SickWDataItem(api_data['id'], api_data)
			elif results.get('error_message'):
				raise monday.api.exceptions.MondayDataError(f"Error Fetching S/N Data: {results['error_message']}")

		if imei_item:
			# already searched for this IMEI, post data to main board
			update += "THIS IMEI HAS BEEN CHECKED BEFORE"
			raw_data = json.loads(imei_item.fetched_data.value)
			update += "\n\nDEVICE DATA"
			for key in raw_data:
				update += f"\n{key}: {raw_data[key]}"
		else:
			sw_imei_url = sickw.helpers.format_url(main.imeisn.value)
			try:
				sw_data = sickw.send_request(sw_imei_url)
			except Exception as e:
				notify_admins_of_error(f"Could Not Fetch SickW Data: {str(e)}")
				main.add_update(f"Could Not Fetch SickW Data: {str(e)}", main.error_thread_id.value)
				raise e
			try:
				raw_data = sickw.helpers.parse_result_to_dict(sw_data)
			except Exception as e:
				notify_admins_of_error(f"Could Not Parse SickW Data: {str(e)}")
				main.add_update(f"Could Not Parse SickW Data: {str(e)}", main.error_thread_id.value)
				raise e

			update += "\n\nDEVICE DATA"
			for key in raw_data:
				update += f"\n{key}: {raw_data[key]}"

			imei_item = sickw.helpers.record_device_information(raw_data)

		main_ids = [str(item) for item in imei_item.main_board_connect.value]

		main_board_imei_search = monday.api.monday_connection.items.fetch_items_by_column_value(
			board_id=main.BOARD_ID,
			column_id=main.imeisn.column_id,
			value=main.imeisn.value
		)

		if not main_board_imei_search.get('error_message'):
			main_ids_from_board = [item['id'] for item in main_board_imei_search['data']['items_page_by_column_values']['items']]
			main_ids.extend([str(item) for item in main_ids_from_board])

		if main_ids:
			update += f"\n\nPREVIOUSLY REPAIRED BY US {len(main_ids)} TIMES"
			for item_id in main_ids:
				update += f"\n{item_id}"

		main.add_update(update, main.notes_thread_id.value)

		return imei_item
