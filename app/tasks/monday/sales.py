import datetime
from dateutil.parser import parse

from ...errors import EricError
from ...services import monday, zendesk
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
		if sale_controller.invoicing_status.value == "Pushed to Invoicing":
			sale_controller.add_update("Already pushed to invoicing, this sale cannot be edited.")
			return sale_controller
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

	if main_item.client.value == "Warranty":
		sale_controller.processing_status = "Warranty"
		sale_controller.commit()
		return sale_controller

	if not main_item.products and not main_item.custom_quote_connect.value:
		sale_controller.processing_status = "No Products"
		sale_controller.commit()
		return sale_controller

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
		if main_item.repaired_date.value:
			sale_controller.date_added = main_item.repaired_date.value
		sale_controller.commit()

		return sale_controller

	except Exception as e:
		notify_admins_of_error(f"Error creating or updating sale: {e}")
		sale_controller.processing_status = "Error"
		sale_controller.commit()
		sale_controller.add_update(f"Error creating or updating sale: {e}")
		raise e


def generate_invoice_from_sale(sale_item_id):
	try:
		sale_item = monday.items.sales.SaleControllerItem(sale_item_id).load_from_api()
		sale_item.add_to_invoice_item()
	except Exception as e:
		notify_admins_of_error(f"Task: Error generating invoice from sale: {e}")
		raise e


def sync_invoice_data_to_xero(invoice_item_id):
	try:
		invoice_item = monday.items.sales.InvoiceControllerItem(invoice_item_id).load_from_api()
		invoice_item.sync_to_xero()
	except Exception as e:
		notify_admins_of_error(f"Task: Error syncing invoice data to xero: {e}")
		raise e


class InvoiceDetailsError(EricError):
	pass
