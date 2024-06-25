import datetime
from dateutil.parser import parse

from zenpy.lib.api_objects import Comment

from ...errors import EricError
from ...services import monday, zendesk, xero
from ...utilities import notify_admins_of_error


def create_or_update_sale(main_id, report_to_main=False):
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

	if main_item.repaired_date.value:
		sale_controller.date_added = main_item.repaired_date.value

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

		sale_controller.commit()

		if report_to_main:
			main_item.add_update(
				f"Sale: https://icorrect.monday.com/boards/6285416596/views/136781267/pulses/{sale_controller.id}",
				thread_id=main_item.high_level_thread_id.value
			)

		return sale_controller

	except Exception as e:
		notify_admins_of_error(f"Error creating or updating sale: {e}")
		sale_controller.processing_status = "Error"
		sale_controller.commit()
		sale_controller.add_update(f"Error creating or updating sale: {e}")
		raise e


def create_or_update_sales_ledger_item(sale_id):
	monday.items.sales.ProductSalesLedgerItem.create_new_record(sale_id)


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


def convert_sale_to_profit_and_loss(sale_item_id):
	try:
		warranty = False

		sale_item = monday.items.sales.SaleControllerItem(sale_item_id).load_from_api()
		main_item = monday.items.MainItem(sale_item.main_item_id.value).load_from_api()

		if main_item.client.value == "Warranty":
			warranty = True

		if not warranty:
			# create a new profit/loss item
			wiwi = monday.items.sales.WasItWorthItItem()
			wiwi.imeisn = main_item.imeisn.value
			wiwi.device_id = str(main_item.device_id)
			wiwi.device_connect = [int(main_item.device_id)]
			wiwi.create(f"{main_item.name}")
		else:
			# get the most recent profit/loss item
			wiwi = monday.items.sales.WasItWorthItItem(search=True)
			search = wiwi.search_board_for_items("imeisn", main_item.imeisn.value)
			if search:
				wiwis_by_imei = sorted([
					monday.items.sales.WasItWorthItItem(item['id'], item) for item in search
				], key=lambda x: x.date_added.value, reverse=True)
				wiwi = wiwis_by_imei[0]
			else:
				raise SalesError(
					"No profit/loss item found for this warranty item: Cannot find original repair details")

		if wiwi.sale_items_connect.value:
			if int(sale_item.id) not in wiwi.sale_items_connect.value:
				wiwi.sale_items_connect = wiwi.sale_items_connect.value.append(int(sale_item.id))
		else:
			wiwi.sale_items_connect = [int(sale_item.id)]

		wiwi.calculation_status = "Processing"
		wiwi.commit()

		sale_item.convert_to_pl_status = "Complete"
		sale_item.commit()

	except Exception as e:
		notify_admins_of_error(f"Task: Error calculating profit and loss: {e}")
		raise e


def calculate_profit_and_loss(wiwi_id):
	wiwi = monday.items.sales.WasItWorthItItem(wiwi_id).load_from_api()
	try:
		wiwi.calculate_profit_loss()
	except Exception as e:
		notify_admins_of_error(f"Task: Error calculating profit and loss: {e}")
		wiwi.calculation_status = "Error"
		wiwi.commit()
		raise e


def notify_of_xero_invoice_payment(invoice_id):
	try:
		invoice = xero.client.get_invoice_by_id(invoice_id)
		zendesk_query = zendesk.client.search(type="ticket", fieldvalue=invoice_id)
		if len(zendesk_query) != 1:
			raise ValueError(f"Expected 1 ticket for Xero Invoice ID {invoice_id}, found {len(zendesk_query)}")

		if invoice['Status'] == 'PAID':
			update = f"Xero Invoice {invoice['InvoiceNumber']} of £{invoice['Total']} has been paid"
			ticket = next(zendesk_query)
			try:
				ticket.comment = Comment(public=False, body=update)
				zendesk.client.tickets.update(ticket)
			except Exception as e:
				raise e
			try:
				main_id_field = [f for f in ticket.custom_fields if f['id'] == zendesk.custom_fields.FIELDS_DICT['main_item_id']][0]
				main_id = main_id_field['value']
				if main_id:
					main_item = monday.items.MainItem(main_id)
					main_item.add_update(update, thread_id=main_item.high_level_thread_id.value)
				elif not main_id:
					raise ValueError("No Main Item ID found in ticket, should be impossible")
			except Exception as e:
				raise e
		elif invoice['Status'] in ('VOIDED', 'DELETED'):
			zendesk_query = zendesk.client.search(type="ticket", fieldvalue=invoice_id)
			ticket = next(zendesk_query)
			ticket.comment = Comment(public=False, body=f"Xero Invoice has been voided or deleted. Check Xero for details.")
			ticket.custom_fields[zendesk.custom_fields.FIELDS_DICT['xero_invoice_id']] = None
			zendesk.client.update_ticket(ticket)
		elif invoice['Status'] == 'DRAFT':
			pass
		else:
			raise ValueError(f"Xero Invoice Status is not PAID, VOIDED or DELETED: {invoice['Status']}")

	except Exception as e:
		notify_admins_of_error(f"Task: Error notifying of Xero invoice payment: {e}")
		raise e


def update_corporate_invoicing_status(invoice_id):
	try:
		invoice = xero.client.get_invoice_by_id(invoice_id)
		invoice_item_search = monday.api.monday_connection.items.fetch_items_by_column_value(
			board_id=monday.items.sales.InvoiceControllerItem.BOARD_ID,
			column_id="text8",
			value=invoice_id
		)
		if invoice_item_search.get('error_code'):
			raise ValueError(f"Error fetching invoice item from Monday: {invoice_item_search['error_message']}")

		results = invoice_item_search['data']['items_page_by_column_values']['items']
		if not results:
			return False

		corporate_invoicing = monday.items.sales.InvoiceControllerItem(results[0]['id'], results[0])

		if invoice['Status'] == 'PAID':
			corporate_invoicing.invoice_status = "PAID"
			corporate_invoicing.commit()
		elif invoice['Status'] == 'AUTHORISED':
			corporate_invoicing.invoice_status = "AUTHORISED"
			corporate_invoicing.commit()
		elif invoice['Status'] in ('VOIDED', 'DELETED'):
			corporate_invoicing.invoice_status = "VOIDED"
			corporate_invoicing.commit()
		elif invoice['Status'] == 'DRAFT':
			pass
		else:
			raise ValueError(f"Xero Invoice Status is not PAID, VOIDED or DELETED: {invoice['Status']}")

	except Exception as e:
		notify_admins_of_error(f"Task: Error updating corporate invoicing status: {e}")
		raise e


class SalesError(EricError):
	pass
