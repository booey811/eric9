from ..api.items import BaseItemType
from ..api import columns


class PartItem(BaseItemType):
	BOARD_ID = 985177480

	stock_level = columns.NumberValue("quantity")
