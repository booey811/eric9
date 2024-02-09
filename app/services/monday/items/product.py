from ..api.items import BaseItemType
from ..api import columns


class ProductItem(BaseItemType):
	BOARD_ID = 349212843

	required_minutes = columns.NumberValue("numbers7")
