import functools
import os

from .. import conf

USER_DATA = [
	{
		"name": "gabe",
		"motion_assignee_id": "vpCL0oYJ2Ocm6WrWXAS1AZXlrPw2",  # gabe
		"slack_id": "U024H79546T",  # gabe
		"monday_id": "4251271",  # gabe
		"repair_group_id": conf.TEST_PROOF_ITEMS  # test proof items group
	},
	{
		"name": "dev",
		"motion_assignee_id": "vpCL0oYJ2Ocm6WrWXAS1AZXlrPw2",  # gabe
		"slack_id": "U024H79546T",  # gabe
		"monday_id": "4251271",  # gabe
		"repair_group_id": conf.MAIN_DEV_GROUP_ID  # test proof items group
	},
	{
		"name": "safan",
		"motion_assignee_id": "vpCL0oYJ2Ocm6WrWXAS1AZXlrPw2",  # gabe
		"slack_id": "U024H79546T",  # gabe
		"monday_id": "4251271",  # gabe
		"repair_group_id": conf.MAIN_DEV_GROUP_ID  # test proof items group
	},
]


def ensure_attribute_set(property_func):
	"""Decorator to ensure a property attribute has been set before accessing it."""

	@functools.wraps(property_func)
	def wrapper(self):
		value = property_func(self)
		if value is None:
			raise AttributeError(f"The attribute '{property_func.__name__}' is not set.")
		return value

	return wrapper


class User:

	def __init__(self, name='', slack_id='', monday_id='', repair_group_id='', motion_assignee_id=''):

		self._name = None
		self._motion_assignee_id = None
		self._slack_id = None
		self._monday_id = None
		self._repair_group_id = None
		self._motion_api_key = None

		try:
			if not name and not slack_id and not monday_id and not repair_group_id and not motion_assignee_id:
				raise RuntimeError("Must use an attribute to search for a user")
			elif name:
				dct = [data for data in USER_DATA if data['name'] == name][0]
			elif slack_id:
				dct = [data for data in USER_DATA if data['slack_id'] == slack_id][0]
			elif monday_id:
				dct = [data for data in USER_DATA if data['monday_id'] == monday_id][0]
			elif repair_group_id:
				dct = [data for data in USER_DATA if data['repair_group_id'] == repair_group_id][0]
			elif motion_assignee_id:
				dct = [data for data in USER_DATA if data['motion_assignee_id'] == motion_assignee_id][0]
			else:
				raise RuntimeError(
					"Must provide input: name, monday_id, slack_id, repair_group_id or motion_assignee_id")

		except IndexError:
			raise ValueError(
				f"No User Found From Search; name:{name} slack_id:{slack_id}, monday_id:{monday_id}, "
				f"repair_group_id::{repair_group_id}, motion_assignee_id:{motion_assignee_id}")

		self._load_data(dct)

	def _load_data(self, user_data: dict):
		self._name = str(user_data.get('name'))
		self._motion_assignee_id = str(user_data.get('motion_assignee_id'))
		self._slack_id = str(user_data.get('slack_id'))
		self._monday_id = str(user_data.get('monday_id'))
		self._repair_group_id = str(user_data.get('repair_group_id'))
		self._motion_api_key = conf.MOTION_KEYS[self._name]

	@property
	@ensure_attribute_set
	def name(self):
		return self._name

	@property
	@ensure_attribute_set
	def motion_assignee_id(self):
		return self._motion_assignee_id

	@property
	@ensure_attribute_set
	def slack_id(self):
		return self._slack_id

	@property
	@ensure_attribute_set
	def monday_id(self):
		return self._monday_id

	@property
	@ensure_attribute_set
	def repair_group_id(self):
		return self._repair_group_id

	@property
	@ensure_attribute_set
	def motion_api_key(self):
		return self._motion_api_key
