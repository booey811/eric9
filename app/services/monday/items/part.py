from ..api.items import BaseCacheableItem, BaseItemType
from ..api import columns, get_api_items, monday_connection, exceptions
from ....utilities import notify_admins_of_error


class PartItem(BaseCacheableItem):
	BOARD_ID = 985177480

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.stock_level = columns.NumberValue("quantity")
		self.products_connect = columns.ConnectBoards("link_to_products___pricing")
		self.supply_price = columns.NumberValue("supply_price")

		self.supplier_connect = columns.ConnectBoards("connect_boards")
		self.reorder_level = columns.NumberValue("numbers")

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

		adjustment.parts_connect = [self.id]
		adjustment.commit()

		return adjustment


class InventoryAdjustmentItem(BaseItemType):
	BOARD_ID = 989490856

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.quantity_before = columns.NumberValue("quantity_before")
		self.difference = columns.NumberValue("numbers9")
		self.quantity_after = columns.NumberValue("quantity_after")
		self.movement_type = columns.StatusValue("movement_type")
		self.movement_direction = columns.StatusValue("dup__of_movement_type")
		self.void_status = columns.StatusValue("status7")

		self.part_id = columns.TextValue("text4")
		self.part_url = columns.LinkURLValue("part_url")

		# self.parts_connect = columns.ConnectBoards("connect_boards9")
		# self.supplier_connect = columns.ConnectBoards("connect_boards")

		# self.auto_order_status = columns.StatusValue("status_1")
		# self.auto_order_minimum = columns.NumberValue("numbers")

		self.source_item_id = columns.TextValue("mainboard_id")
		self.source_url = columns.LinkURLValue("link2")

		super().__init__(item_id, api_data, search)

	def void_self(self):
		part = PartItem(self.part_id.value)

		difference = -int(self.difference.value)

		part.adjust_stock_level(
			difference,
			source_item=self,
			movement_type='Void Resolution'
		)

		self.void_status = "Voided"
		self.commit()


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


class StockCheckoutControlItem(BaseItemType):
	BOARD_ID = 6267736041

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.main_item_id = columns.TextValue("text")
		self.main_item_connect = columns.ConnectBoards("connect_boards")
		self.repair_status = columns.StatusValue("status47")
		self.profile_status = columns.StatusValue("status4")
		self.checkout_status = columns.StatusValue("status3")

		self.checkout_line_ids = columns.ConnectBoards("subitems")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class StockCheckoutLineItem(BaseItemType):
	BOARD_ID = 6267766059

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.line_checkout_status = columns.StatusValue("status0")
		self.parts_cost = columns.NumberValue("numbers")
		self.part_id = columns.TextValue("text")
		self.inventory_movement_id = columns.TextValue("text1")

		super().__init__(item_id=item_id, api_data=api_data, search=search)


class RepairMapItem(BaseItemType):
	BOARD_ID = 984924063

	REPAIRS_WITH_COLOUR = (
		'TrackPad',
		'Charging Port',
		'Headphone Jack',
		'Home Button',
		'Front Screen Universal',
		'Rear Glass',
		'Front Screen (LG)',
		'Front Screen (Tosh)',
		'Rear Housing',
		'TEST Screen',
		'Front Screen',
		'After Market OLED'
	)

	@classmethod
	def fetch_by_combined_ids(cls, combined=None, dual=None):
		if (not dual and not combined) or (combined and dual):
			raise ValueError("Use Combined or Dual IDs, not both")

		if combined:
			search_col_id = "combined_id"
			search_val = combined
		elif dual:
			search_col_id = "dual_id"
			search_val = dual
		else:
			raise ValueError("Impossible Input")

		results = monday_connection.items.fetch_items_by_column_value(
			board_id=cls.BOARD_ID,
			column_id=search_col_id,
			value=search_val
		)

		if results.get('error_message'):
			raise exceptions.MondayAPIError(results.get("error_message"))

		else:
			return [cls(_['id'], _) for _ in results['data']['items_page_by_column_values']['items']]

	@classmethod
	def fetch_by_deprecated_column_numbers(cls, device_no, parts_used_no, colour_no, has_colour):
		dual_val = f"{device_no}-{parts_used_no}"
		if has_colour:
			combined_val = f"{device_no}-{parts_used_no}-{colour_no}"
		else:
			combined_val = dual_val

		results = monday_connection.items.fetch_items_by_column_value(
			board_id=cls.BOARD_ID,
			column_id="combined_id",  # dual ID columns
			value=combined_val
		)

		if results.get('error_code'):
			notify_admins_of_error(f"Could Not Find Repair Map: {results}")
			raise exceptions.MondayAPIError(results.get('error_message'))
		else:
			results = results['data']['items_page_by_column_values']['items']

		if len(results) != 1:
			results = monday_connection.items.fetch_items_by_column_value(
				board_id=cls.BOARD_ID,
				column_id="dual_only_id",  # combined ID column
				value=dual_val
			)
			if results.get('error_code'):
				notify_admins_of_error(f"Could Not Find Repair Map: {results}")
				raise exceptions.MondayAPIError(results.get('error_message'))
			else:
				results = results['data']['items_page_by_column_values']['items']

		if len(results) != 1:
			results = monday_connection.items.fetch_items_by_column_value(
				board_id=cls.BOARD_ID,
				column_id="combined_id",  # combined ID column
				value=dual_val
			)
			if results.get('error_code'):
				notify_admins_of_error(f"Could Not Find Repair Map: {results}")
				raise exceptions.MondayAPIError(results.get('error_message'))
			else:
				results = results['data']['items_page_by_column_values']['items']

			if not results:
				return None

		items = [cls(_['id'], _) for _ in results]
		try:
			return items[0]
		except IndexError:
			return None

	def __init__(self, item_id=None, api_data=None, search=False):
		self.part_ids = columns.ConnectBoards("connect_boards5")

		self.device_col_number = columns.TextValue("device_id")
		self.parts_used_col_number = columns.TextValue("repair_id")
		self.colour_col_number = columns.TextValue("colour_id")

		self.combined_id = columns.TextValue("combined_id")
		self.dual_id = columns.TextValue("dual_only_id")

		super().__init__(item_id, api_data, search)


class RefurbMenuItem(BaseItemType):
	BOARD_ID = 1106794399

	def __init__(self, item_id=None, api_data=None, search=False):

		self.processing_status = columns.StatusValue("status2")

		self.part_connect = columns.ConnectBoards("connect_boards")
		self.quantity_to_add = columns.NumberValue("numbers4")

		super().__init__(item_id, api_data, search)


class RefurbOutputItem(BaseItemType):

	BOARD_ID = 3382612900

	def __init__(self, item_id=None, api_data=None, search=False):

		self.part_id = columns.TextValue("text")
		self.parts_movement_id = columns.TextValue("text__1")

		self.batch_size = columns.NumberValue("numbers")

		self.refurb_consumption_status = columns.StatusValue("status1")
		self.parts_adjustment_status = columns.StatusValue("status6")

		super().__init__(item_id, api_data, search)


class WasteItem(BaseItemType):
	BOARD_ID = 1157165964

	def __init__(self, item_id=None, api_data=None, search=False):

		self.reason = columns.TextValue("waste_description")
		self.part_id = columns.TextValue("partboard_id")
		self.parts_connect = columns.ConnectBoards("connect_boards")

		self.recorded_by = columns.PeopleValue("people")
		self.movement_item_id = columns.TextValue("text__1")

		self.stock_adjust_status = columns.StatusValue("waste_status")

		super().__init__(item_id, api_data, search)

	def process_stock_adjustment(self, part: PartItem = None):
		if not part and not self.part_id.value:
			raise exceptions.MondayDataError(f"{self} has no Part ID")
		elif not part:
			part = PartItem(self.part_id.value)
		else:
			raise Exception("Part ID and Part Object Provided")

		if self.movement_item_id.value:
			mov_item = InventoryAdjustmentItem(self.movement_item_id.value)
			mov_item.void_self()
			self.movement_item_id = ''

		movement_item = part.adjust_stock_level(-1, self, 'Damaged')
		self.movement_item_id = str(movement_item.id)
		self.stock_adjust_status = 'Complete'
		self.commit()
		return part
