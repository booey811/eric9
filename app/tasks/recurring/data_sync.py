import logging

from app.services import monday
from app.services.monday import items
from app.services import zendesk

log = logging.getLogger('eric')


class ZendeskDataSync:

	@staticmethod
	def sync_device_field_options():
		log.debug("Syncing Device Field")
		device_field_id = 17862174043537
		all_devices = items.DeviceItem.fetch_all()
		results = []
		for device in all_devices:
			zendesk_tag = f"device__{device.id}"
			option_name = f"{device.device_type.value}::{device.name}"
			log.debug(f"Creating option: {option_name} | {zendesk_tag}")
			results.append(zendesk.helpers.create_ticket_field_option(
				ticket_field_id=device_field_id,
				option_name=option_name,
				option_tag=zendesk_tag
			))
		return results

	@staticmethod
	def sync_product_field_options():
		log.debug("Syncing Product Field")
		product_field_id = 360011640097
		all_products = items.ProductItem.fetch_all()
		results = []
		for product in all_products:
			device_id = product.device_id
			if device_id:
				device_data = monday.api.get_api_items([product.device_id])[0]
				device = items.DeviceItem(device_data['id'], device_data)
				option_name = f"{device.device_type.value}::{device.name}::{product.name} (£{product.price.value})"
			else:
				option_name = f"Device::Other Device::{product.name} (£{product.price.value})"

			zendesk_tag = f"product__{product.id}"
			log.debug(f"Creating option: {option_name} | {zendesk_tag}")
			results.append(zendesk.helpers.create_ticket_field_option(
				ticket_field_id=product_field_id,
				option_name=option_name,
				option_tag=zendesk_tag
			))
		return results

