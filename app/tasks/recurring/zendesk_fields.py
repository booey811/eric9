from app.services import zendesk

if __name__ == '__main__':
	zendesk.custom_fields.sync_product_field_options()
	zendesk.custom_fields.sync_device_field_options()
