import logging

from moncli.models import MondayModel
from moncli import types as col_types

from app.models.base import BaseEricModel

log = logging.getLogger('eric')


class _BaseRepairPhaseModel(MondayModel):
	description = col_types.LongTextType(id='long_text')


class _BaseRepairPhaseLineItem(MondayModel):
	phase_entity_connect = col_types.ItemLinkType(id='connect_boards')
	minutes_from_phase_entity = col_types.NumberType(id='mirror1')
	minutes_from_override = col_types.NumberType(id='numbers')


class _BaseRepairPhaseEntityModel(MondayModel):
	pass


class RepairPhaseModel(BaseEricModel):
	MONCLI_MODEL = _BaseRepairPhaseModel

	"""
	Represents a repair phase in the monday.com board, items of the Repair Phase Model Board
	"""

	def __init__(self, repair_phase_id, moncli_item=None):
		super().__init__(repair_phase_id, moncli_item)


class RepairPhaseLineItem(BaseEricModel):
	BOARD_ID = 5959544342  # Repair Phase Models Subitems Board
	MONCLI_MODEL = _BaseRepairPhaseLineItem

	"""
	Represents a repair phase line item in the monday.com board, subitems of the Repair Phase Models Board
	"""

	def __init__(self, repair_phase_line_item_id, moncli_item=None):
		super().__init__(repair_phase_line_item_id, moncli_item)

	@property
	def phase_entities(self):
		"""
		Return the repair phase entities for this repair phase line item.
		"""
		return [RepairPhaseEntity(item_id) for item_id in self.model.phase_entity_connect]

	@property
	def minutes_from_phase_entities(self):
		"""
		Return the minutes from phase entities for this repair phase line item, taking into account the
		override column if required.
		"""

		if self.model.minutes_from_override:
			return self.model.minutes_from_override
		else:
			mirror_col_id = 'mirror1'
			try:
				log.debug('Getting mirror column value')
				hacky_col_val = [col for col in self.model.item.column_values if col.id == mirror_col_id][0]
			except IndexError:
				raise ValueError(f"Column {mirror_col_id} not found in {self}")


class RepairPhaseEntity(BaseEricModel):
	MONCLI_MODEL = _BaseRepairPhaseEntityModel

	"""
	Represents a repair phase entity in the monday.com board.
	"""

	def __init__(self, repair_phase_entity_id, moncli_item=None):
		super().__init__(repair_phase_entity_id, moncli_item)
