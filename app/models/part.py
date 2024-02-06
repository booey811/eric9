from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel


class _BasePartModel(MondayModel):
	stock_level = col_type.NumberType(id='quantity')


class PartModel(BaseEricModel):
	MONCLI_MODEL = _BasePartModel

	def __init__(self, item_id, moncli_item=None):
		super().__init__(item_id, moncli_item)

	def __str__(self):
		return f"PartModel({self.id}): {self._name or 'Not Fetched'}"

	@property
	def model(self) -> _BasePartModel:
		return super().model
