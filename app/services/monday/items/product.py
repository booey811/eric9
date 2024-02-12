from ..api.items import BaseItemType
from ..api import columns


class ProductItem(BaseItemType):
	BOARD_ID = 2477699024

	device_connect = columns.ConnectBoards("link_to_devices6")
	parts_connect = columns.ConnectBoards("connect_boards8")

	price = columns.NumberValue("numbers")

	required_minutes = columns.NumberValue("numbers7")
	woo_commerce_product_id = columns.TextValue("text3")

	@property
	def device_id(self):
		if self.device_connect.value:
			return self.device_connect.value[0]
		else:
			return None