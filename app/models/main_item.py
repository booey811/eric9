import moncli
from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel


class _BaseMainModel(MondayModel):
	hard_deadline = col_type.DateType(id='date36')
	phase_deadline = col_type.DateType(id='date19')
	description = col_type.TextType(id='text368')
	motion_task_id = col_type.TextType(id='text76')


class MainModel(BaseEricModel):

	MONCLI_MODEL = _BaseMainModel

	def __init__(self, main_item_id, moncli_item: moncli.en.Item = None):
		super().__init__(main_item_id, moncli_item)
