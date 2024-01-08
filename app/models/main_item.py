import moncli
from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel


class _BaseMainModel(MondayModel):
	hard_deadline = col_type.DateType(id='date36')
	description = col_type.TextType(id='text368')


class MainModel(BaseEricModel):

	MONCLI_MODEL = _BaseMainModel

	def __init__(self, main_item_id, moncli_item: moncli.en.Item = None):
		super().__init__(main_item_id, moncli_item)
