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

		sale_controller.create_invoice_item()

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


def generate_invoice_item_data(invoice_item_id, main_item=None, sale_item=None):
	sale_item = monday.items.sales.SaleControllerItem(sale_item_id).load_from_api()
	try:
		main_item = monday.items.MainItem(sale_item.main_item_id.value).load_from_api()

		ticket = zendesk.client.tickets(id=int(main_item.ticket_id.value))
		organization = ticket.organization

		if sale_item.company_short_code.value:
			corp_item = monday.items.corporate.base.CorporateAccountItem.get_by_short_code(
				sale_item.company_short_code.value)
		elif organization:
			corp_item_id = organization.organization_fields['corporateboard_id']
			corp_item = monday.items.corporate.base.CorporateAccountItem(int(corp_item_id)).load_from_api()
		else:
			raise InvoiceDetailsError(
				f"{ticket.id}: No organization found on ticket and no short code on sale item: Cannot Find Account Item"
			)



	# create the invoice
	# logical route info:
	# monthly invoicing; check for a draft, add to it if found, else create a new one
	# pay per repair; create a new invoice

	except InvoiceDetailsError as e:
		notify_admins_of_error(f"Invoice Details Error: {e}")
		sale_item.invoicing_status = "Missing Info"
		sale_item.commit()
		sale_item.add_update(f"Invoice Details Error: {e}")
		raise e

	except Exception as e:
		notify_admins_of_error(f"Error creating invoice: {e}")
		sale_item.invoicing_status = "Error"
		sale_item.commit()
		sale_item.add_update(f"Error creating invoice: {e}")
		raise e


class InvoiceDetailsError(EricError):
	pass
