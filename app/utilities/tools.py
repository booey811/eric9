import inspect
import importlib
import pkgutil

from ..services.monday import items as items_package, api as api_package
from ..services.monday.api.columns import ValueType


class MondayTools:

	@staticmethod
	def find_class_with_board_id(b_id):
		package = items_package
		prefix = package.__name__ + "."

		for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
			module = importlib.import_module(modname)
			for name, obj in inspect.getmembers(module, inspect.isclass):
				if hasattr(obj, 'BOARD_ID'):
					if str(obj.BOARD_ID) == str(b_id):
						return obj
		return None

	@staticmethod
	def list_redundant_columns(board_id, delete_columns=False):
		"""
		Find columns that are not used by any items in the board
		"""
		desired_class = MondayTools.find_class_with_board_id(board_id)
		if not desired_class:
			raise Exception(f"Class not found for board_id:{board_id}")

		class_col_ids = []
		desired_instance = desired_class()
		instance_attributes = vars(desired_instance)
		for i_att in instance_attributes:
			if hasattr(instance_attributes[i_att], 'column_id'):
				class_col_ids.append(instance_attributes[i_att].column_id)

		board = api_package.boards.get_board(board_id)
		board_columns = board['columns']

		unused_ids = []
		for b_col in board_columns:
			if b_col['id'] not in class_col_ids:
				if b_col['type'] not in ('name', 'subtasks'):
					print(f"Column {b_col['title']} ({b_col['id']}) is not used by any items in the board")
					unused_ids.append(b_col['id'])

		return unused_ids

