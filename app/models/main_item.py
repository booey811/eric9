import logging

import moncli
from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel
from .product import ProductModel
from .repair_phases import RepairPhaseModel

log = logging.getLogger('eric')


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

	def get_phase_model(self):
		prods = [ProductModel(_) for _ in self.model.products_connect]
		if not prods:
			phase_model = RepairPhaseModel(5959544605)
			log.warning(f"No products connected to {self.model.name}, using default phase model: {phase_model}")
		else:
			phase_models = [RepairPhaseModel(p.phase_model_id) for p in prods]
			# get the phase model with the highest total time, calculated by individual line items having required minutes
			for phase_mod in phase_models:
				lines = phase_mod.phase_line_items
				total = sum([line.required_minutes for line in lines])
				phase_mod.total_time = total
			phase_model = max(phase_models, key=lambda x: x.total_time)
		return phase_model

	def get_next_phase(self):
		# get_phase_model, then look at line items and match self.phase_status to line item mainboard_repair_status
		phase_model = self.get_phase_model()
		lines = set(phase_model.phase_line_items)
		for i, line in enumerate(lines):
			print(line.name)
			if line.phase_entity.main_board_phase_label == self.model.repair_phase:
				# Check if there is a next item
				if i + 1 < len(lines):
					next_line = lines[i + 1]
					return next_line
				else:
					# There is no next item, handle accordingly
					return None
