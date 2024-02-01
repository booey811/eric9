import moncli
from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel


class _BaseMainModel(MondayModel):
	# basic info
	main_status = col_type.StatusType(id='status4')

	# device/repair info
	description = col_type.TextType(id='text368')
	requested_repairs = col_type.TextType(id='text368')
	products_connect = col_type.ItemLinkType(id='board_relation', multiple_values=True)

	# scheduling info
	technician = col_type.PeopleType(id='person')
	hard_deadline = col_type.DateType(id='date36')
	phase_deadline = col_type.DateType(id='date65', has_time=True)

	motion_task_id = col_type.TextType(id='text76')
	motion_scheduling_status = col_type.StatusType(id='status_19')

	# phase info
	repair_phase = col_type.StatusType(id='status_177')
	phase_status = col_type.StatusType(id='status_110')


class MainModel(BaseEricModel):
	MONCLI_MODEL = _BaseMainModel

	def __init__(self, main_item_id, moncli_item: moncli.en.Item = None):
		super().__init__(main_item_id, moncli_item)

	@property
	def model(self) -> _BaseMainModel:
		return super().model
