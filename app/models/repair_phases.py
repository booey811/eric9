# import logging
# from typing import List
#
# from moncli.models import MondayModel
# from moncli import types as col_types
#
# from ..models.base import BaseEricModel
# from ..services import monday
# from ..utilities import notify_admins_of_error
#
# log = logging.getLogger('eric')
#
#
# class _BaseRepairPhaseEntityModel(MondayModel):
# 	required_minutes = col_types.NumberType(id='numbers')
# 	main_board_phase_label = col_types.StatusType(id='color')
#
#
# class RepairPhaseEntity(BaseEricModel):
# 	MONCLI_MODEL = _BaseRepairPhaseEntityModel
#
# 	"""
# 	Represents a repair phase entity in the monday.com board.
# 	"""
#
# 	def __init__(self, repair_phase_entity_id, moncli_item=None):
# 		super().__init__(repair_phase_entity_id, moncli_item)
#
# 	def __str__(self):
# 		return f"PhaseEntity({self.id}): {self._name or 'Not Fetched'}"
#
# 	@property
# 	def required_minutes(self):
# 		"""
# 		Return the required minutes for this repair phase entity.
# 		"""
# 		return self.model.required_minutes
#
# 	@property
# 	def main_board_phase_label(self):
# 		"""
# 		Return the main board phase label for this repair phase entity.
# 		"""
# 		return self.model.main_board_phase_label
#
#
# class _BaseRepairPhaseLineItem(MondayModel):
# 	phase_entity_connect = col_types.ItemLinkType(id='connect_boards', multiple_values=False)
# 	minutes_from_phase_entity = col_types.NumberType(id='mirror1')
# 	minutes_from_override = col_types.NumberType(id='numbers')
# 	sort_order = col_types.NumberType(id='numbers5')
#
#
# class RepairPhaseLineItem(BaseEricModel):
# 	BOARD_ID = 5959544342  # Repair Phase Models Subitems Board
# 	MONCLI_MODEL = _BaseRepairPhaseLineItem
#
# 	"""
# 	Represents a repair phase line item in the monday.com board, subitems of the Repair Phase Models Board
# 	"""
#
# 	def __init__(self, repair_phase_line_item_id, moncli_item=None):
# 		super().__init__(repair_phase_line_item_id, moncli_item)
#
# 		self._phase_entity = None
#
# 	def __str__(self):
# 		return f"PhaseLine({self.id}): {self._name or 'Not Fetched'}"
#
#
# 	@property
# 	def phase_entity(self):
# 		"""
# 		Return the repair phase entities for this repair phase line item.
# 		"""
# 		if not self._phase_entity:
# 			self._phase_entity = RepairPhaseEntity(self.model.phase_entity_connect)
# 		return self._phase_entity
#
# 	@property
# 	def required_minutes(self):
# 		"""
# 		Return the minutes from the phase entity for this repair phase line item.
# 		"""
# 		if self.model.minutes_from_override:
# 			return self.model.minutes_from_override
# 		return self.phase_entity.required_minutes
#
#
# class _BaseRepairPhaseModel(MondayModel):
# 	description = col_types.LongTextType(id='long_text')
#
#
# class RepairPhaseModel(BaseEricModel):
# 	MONCLI_MODEL = _BaseRepairPhaseModel
#
# 	"""
# 	Represents a repair phase in the monday.com board, items of the Repair Phase Model Board
# 	"""
#
# 	def __init__(self, repair_phase_id, moncli_item=None):
# 		super().__init__(repair_phase_id, moncli_item)
#
# 		self._phase_line_items = None
#
# 	def __str__(self):
# 		return f"PhaseModel({self.id}): {self._name or 'Not Fetched'}"
#
# 	@property
# 	def phase_line_items(self) -> List[RepairPhaseLineItem]:
# 		"""
# 		Return the repair phase line items for this repair phase.
# 		"""
# 		if not self._phase_line_items:
# 			subitems = self.model.item.get_subitems()
# 			subitems = monday.get_items([s.id for s in subitems], column_values=True)
# 			phase_lines = [RepairPhaseLineItem(s.id, s) for s in subitems]
# 			for p in phase_lines:
# 				if p.model.sort_order is None:
# 					p.model.sort_order = 99
# 					log.error(f"Repair Phase Line Item {p.id} has no sort order, defaulting to 99")
# 					notify_admins_of_error(f"{str(self)} has no sort order, defaulting to 99")
# 			self._phase_line_items = sorted(phase_lines, key=lambda x: x.model.sort_order)
# 		return self._phase_line_items
