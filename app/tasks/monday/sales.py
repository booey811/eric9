from ...services import monday
from ...utilities import notify_admins_of_error


def create_or_update_sale(main_id):
	# get the main item
	main_item = monday.items.MainItem(main_id)

	# get the sale controller item
	search = monday.items.sales.SaleControllerItem().search_board_for_items("main_item_id", str(main_id))
	if not search:
		sale_controller = monday.items.sales.SaleControllerItem()
		sale_controller.main_item_id = str(main_id)
		sale_controller.main_item_connect = [int(main_id)]
		sale_controller.create(main_item.name)
	else:
		sale_controller = monday.items.sales.SaleControllerItem(search[0]['id'], search[0])
	try:
		# remove old sale lines
		current_sale_line_ids = sale_controller.subitem_ids.value or []
		for _id in current_sale_line_ids:
			monday.api.monday_connection.items.delete_item_by_id(int(_id))
	except Exception as e:
		notify_admins_of_error(f"Error removing old sale lines: {e}")
		sale_controller.processing_status = "Error"
		sale_controller.commit()
		sale_controller.add_update(f"Error removing old sale lines: {e}")
		raise e

	try:
		# add products
		for prod in main_item.products:

			price = prod.price.value

			blank_line = monday.items.sales.SaleLineItem()
			blank_line.line_type = "Standard Product"
			if price:
				blank_line.price_inc_vat = int(price)
			blank_line.source_id = str(prod.id)
			line = monday.api.monday_connection.items.create_subitem(
				parent_item_id=sale_controller.id,
				subitem_name=prod.name,
				column_values=blank_line.staged_changes
			)

		custom_quote_ids = main_item.custom_quote_connect.value

		# add custom quotes
		if custom_quote_ids:
			api_data = monday.api.get_api_items(custom_quote_ids)
			customs = [monday.items.misc.CustomQuoteLineItem(item['id'], item) for item in api_data]
			for custom in customs:
				price = custom.price.value
				blank_line = monday.items.sales.SaleLineItem()
				blank_line.line_type = "Custom Quote"
				if price:
					blank_line.price_inc_vat = int(price)
				blank_line.source_id = str(custom.id)
				line = monday.api.monday_connection.items.create_subitem(
					parent_item_id=sale_controller.id,
					subitem_name=custom.name,
					column_values=blank_line.staged_changes
				)
		sale_controller.processing_status = "Complete"
		sale_controller.commit()
		return sale_controller

	except Exception as e:
		notify_admins_of_error(f"Error creating or updating sale: {e}")
		sale_controller.processing_status = "Error"
		sale_controller.commit()
		sale_controller.add_update(f"Error creating or updating sale: {e}")
		raise e
