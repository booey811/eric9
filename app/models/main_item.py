import logging

import moncli
from moncli.models import MondayModel
from moncli import types as col_type

from .base import BaseEricModel
from .product import ProductModel
from .repair_phases import RepairPhaseModel
from .part import PartModel
from ..utilities import notify_admins_of_error
from ..services import monday
from ..errors import EricError

log = logging.getLogger('eric')


class _BaseMainModel(MondayModel):
	# basic info
	main_status = col_type.StatusType(id='status4')
	service = col_type.StatusType(id='service')
	client = col_type.StatusType(id='status')
	repair_type = col_type.StatusType(id='status24')

	# date info
	booking_date = col_type.DateType(id='date6', has_time=True)

	# user info
	ticket_url = col_type.LinkType(id='link1')
	ticket_id = col_type.TextType(id='text6')
	notifications_status = col_type.StatusType(id='status_18')
	email = col_type.TextType(id='text5')
	phone = col_type.TextType(id='text00')

	# address info
	point_of_collection = col_type.TextType(id='text36')
	address_comment = col_type.TextType(id='dup__of_passcode')
	address_street = col_type.TextType(id='passcode')
	address_postcode = col_type.TextType(id='text93')

	# device/repair info
	description = col_type.TextType(id='text368')
	requested_repairs = col_type.TextType(id='text368')
	products_connect = col_type.ItemLinkType(id='board_relation', multiple_values=True)
	device_connect = col_type.ItemLinkType(id='board_relation5', multiple_values=False)

	# payment info
	pay_method = col_type.StatusType(id='payment_method')
	pay_status = col_type.StatusType(id='payment_status')

	# scheduling info
	technician = col_type.PeopleType(id='person')
	hard_deadline = col_type.DateType(id='date36')
	phase_deadline = col_type.DateType(id='date65', has_time=True)

	motion_task_id = col_type.TextType(id='text76')
	motion_scheduling_status = col_type.StatusType(id='status_19')

	# phase info
	repair_phase = col_type.StatusType(id='status_177')
	phase_status = col_type.StatusType(id='status_110')

	# notes threads
	notes_thread_id = col_type.TextType(id='text03')
	error_thread_id = col_type.TextType(id='text34')
	email_thread_id = col_type.TextType(id='text_1')


class MainModel(BaseEricModel):
	MONCLI_MODEL = _BaseMainModel
	BOARD_ID = 349212843

	def __init__(self, main_item_id, moncli_item: moncli.en.Item = None):
		super().__init__(main_item_id, moncli_item)

	def __str__(self):
		return f"MainModel({self.id}): {self._name or 'Not Fetched'}"

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
		lines = phase_model.phase_line_items
		log.debug(f"Got {len(lines)} phase lines:")
		for line in lines:
			log.debug(str(line))
		for i, line in enumerate(lines):
			log.debug(str(line))
			if line.phase_entity.main_board_phase_label == self.model.repair_phase:
				# Check if there is a next item
				if i + 1 < len(lines):
					next_line = lines[i + 1]
					return next_line
				else:
					# There is no next item, handle accordingly
					return None

	def get_thread(self, thread_name):
		log.debug(f"{str(self)} getting thread: {thread_name}")
		if thread_name == 'emails':
			thread_id = self.model.email_thread_id
		elif thread_name == 'notes':
			thread_id = self.model.notes_thread_id
		elif thread_name == 'errors':
			thread_id = self.model.error_thread_id
		else:
			raise Exception(f"Invalid Thread Name: {thread_name}")

		if not thread_id:
			# need to create the thread
			log.debug("Creating thread....")
			update = f"*****  {thread_name.upper()}  *****"
			res = self.model.item.add_update(update)
			thread_id = str(res.id)
			if thread_name == 'emails':
				self.model.email_thread_id = thread_id
			elif thread_name == 'notes':
				self.model.notes_thread_id = thread_id
			elif thread_name == 'errors':
				self.model.error_thread_id = thread_id
			else:
				raise Exception(f"Invalid Thread Name: {thread_name}")
			self.model.save()
			log.debug(f"Created thread: {thread_name} w/ ID: {thread_id}")

		try:
			thread = [
				item for item in self.model.item.get_updates() if str(item.id) == thread_id
			][0]
		except IndexError:
			notify_admins_of_error(f"{str(self)} could not find {thread_name} thread w/ ID: {thread_id}")
			raise EricError(f"{str(self)} could not find {thread_name} thread w/ ID: {thread_id}")

		return thread

	def print_stock_check(self):
		log.debug(f"Checking stock for {str(self)}")

		update = '=== STOCK CHECK ===\n'
		try:
			in_stock = True
			prods = [ProductModel(_) for _ in self.model.products_connect]
			for prod in prods:
				update += prod.name.upper() + '\n'
				if not prod.model.parts_connect:
					message = f"""No parts connected!!!
					Click to fix my connecting parts to this product by making sure the 'parts' column is filled in
					https://icorrect.monday.com/boards/2477699024/views/55887964/pulses/{prod.id}"""
					notify_admins_of_error(message)
					update += message + '\n'

				else:
					part_items = monday.get_items(prod.model.parts_connect, True)
					parts = [PartModel(_.id, _) for _ in part_items]
					for part in parts:
						update += f"{part.model.name}: {part.model.stock_level}\n"

			if in_stock:
				update += "All parts in stock"
			else:
				update += "SOME PARTS MAY NOT BE AVAILABLE"

		except Exception as e:
			log.error(f"Error checking stock for {str(self)}: {e}")
			notify_admins_of_error(f"Error checking stock for {str(self)}: {e}")
			update += f"Error checking stock: {e}"
			log.debug(update)
			self.model.item.add_update(update)
			raise e

		log.debug(update)
		notes_thread = self.get_thread('notes')
		try:
			notes_thread.add_reply(update)
		except Exception as e:
			notify_admins_of_error(f"Error adding stock check update to {str(self)}: {e}")
			try:
				notes_thread.add_reply(update.replace('"', '').replace("/", ''))
			except Exception as e:
				notify_admins_of_error(f"Error adding stock check update (even after parsing) to {str(self)}: {e}")
				raise e

		return update
