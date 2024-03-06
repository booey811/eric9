from ..api.items import BaseCacheableItem, BaseItemType
from ..api import columns, get_api_items
from ....utilities import notify_admins_of_error


class PartItem(BaseCacheableItem):
	BOARD_ID = 985177480

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.stock_level = columns.NumberValue("quantity")
		self.products_connect = columns.ConnectBoards("link_to_products___pricing")

		self._product_ids = None

		super().__init__(item_id, api_data, search)

	@classmethod
	def fetch_all(cls, *args):
		return super().fetch_all("part:")

	@classmethod
	def get(cls, part_ids):
		results = []
		failed = []
		try:
			for _ in part_ids:
				try:
					part = cls(_).load_from_cache()
					results.append(part)
				except Exception as e:
					notify_admins_of_error(f"Error fetching part{_} from cache: {str(e)}")
					failed.append(_)

			if failed:
				part_data = get_api_items(failed)
				for part_info in part_data:
					part = cls(part_info['id'], part_info)
					results.append(part)
		except TypeError as e:
			raise e
		except Exception as e:
			notify_admins_of_error(f"Error fetching parts {part_ids}: {str(e)}")

		return results

	def cache_key(self):
		return f"part:{self.id}"

	def prepare_cache_data(self):
		return {
			"stock_level": self.stock_level.value,
			"id": self.id,
			"product_ids": self._product_ids,
			"name": self.name
		}

	def load_from_cache(self, cache_data=None):
		if not cache_data:
			cache_data = self.fetch_cache_data()
		self.stock_level.value = cache_data['stock_level']
		self._product_ids = cache_data['product_ids']
		self.id = cache_data['id']
		self.name = cache_data['name']
		return self

	@property
	def product_ids(self):
		if self._product_ids is None:
			try:
				self._product_ids = [str(_) for _ in self.products_connect.value]
			except TypeError:
				# notify_admins_of_error(f"Part {self.id} has no product connection")
				self._product_ids = []
		return self._product_ids

	def adjust_stock_level(self, adjustment_quantity, source_item, movement_type):
		if not self._api_data:
			self.load_from_api()
		desired_quantity = self.stock_level.value + adjustment_quantity
		return self.set_stock_level(desired_quantity, source_item, movement_type)

	def set_stock_level(self, desired_quantity, source_item, movement_type):

		if not self._api_data:
			self.load_from_api()

		quantity_before = self.stock_level.value
		difference = desired_quantity - quantity_before
		quantity_after = desired_quantity

		if difference < 0:
			movement_direction = "Out"
		else:
			movement_direction = 'In'

		adjustment = InventoryAdjustmentItem()

		adjustment.quantity_before = int(quantity_before)
		adjustment.difference = int(difference)
		adjustment.quantity_after = int(quantity_after)
		adjustment.source_item_id = str(source_item.id)
		adjustment.source_url = [source_item.name,
								 f"https://icorrect.monday.com/boards/{source_item.BOARD_ID}/pulses/{source_item.id}"]
		adjustment.movement_type = str(movement_type)
		adjustment.movement_direction = movement_direction

		adjustment.part_id = str(self.id)
		adjustment.part_url = [self.name, f"https://icorrect.monday.com/boards/{self.BOARD_ID}/pulses/{self.id}"]

		adjustment.create(name=str(self.name))

		self.stock_level = desired_quantity
		self.commit()

		return adjustment


class InventoryAdjustmentItem(BaseItemType):
	BOARD_ID = 989490856

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.quantity_before = columns.NumberValue("quantity_before")
		self.difference = columns.NumberValue("numbers9")
		self.quantity_after = columns.NumberValue("quantity_after")
		self.movement_type = columns.StatusValue("movement_type")
		self.movement_direction = columns.StatusValue("dup__of_movement_type")

		self.part_id = columns.TextValue("text4")
		self.part_url = columns.LinkURLValue("part_url")

		self.source_item_id = columns.TextValue("mainboard_id")
		self.source_url = columns.LinkURLValue("link2")

		super().__init__(item_id, api_data, search)


class OrderItem(BaseItemType):
	BOARD_ID = 2854362805

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.app_meta = columns.LongTextValue("long_text")
		self.order_status = columns.StatusValue("status7")
		self.subitem_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id, api_data, search)


class OrderLineItem(BaseItemType):
	BOARD_ID = 2854374997

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.part_id = columns.TextValue("text")
		self.price = columns.NumberValue("numbers_1")
		self.quantity = columns.NumberValue("numbers5")
		self.processing_status = columns.StatusValue("status6")

		super().__init__(item_id, api_data, search)
