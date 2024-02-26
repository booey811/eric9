from ..api.items import BaseCacheableItem
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
