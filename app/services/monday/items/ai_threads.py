from ..api.items import BaseItemType, MondayAPIError
from ..api import columns, monday_connection, get_api_items


class BaseAIThreadItem(BaseItemType):

	ASSISTANT_ID = None

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):
		super().__init__(item_id, api_data, search, cache_data)


class InvoiceAssistantThreadItem(BaseAIThreadItem):
	BOARD_ID = 6682296586
	ASSISTANT_ID = "asst_n6uFW0EtkuBfEbEHtUUbqsvT"

	@classmethod
	def get_by_message_ts(cls, message_ts):
		results = monday_connection.items.fetch_items_by_column_value(
			cls.BOARD_ID,
			column_id="text1__1",
			value=message_ts
		)
		if results.get('error_message'):
			raise MondayAPIError(results['error_message'])

		if len(results['data']['items_page_by_column_values']['items']) == 1:
			obj = cls(results['data']['items_page_by_column_values']['items'][0]['id']).load_from_api()
			obj.load_from_api()
			return obj
		else:
			raise MondayAPIError(f"Too Many Thread Items ({len(results['data']['items_page_by_column_values']['items'])}) with message_ts {message_ts}")

	@classmethod
	def get_by_thread_id(cls, thread_id):
		results = monday_connection.items.fetch_items_by_column_value(
			cls.BOARD_ID,
			column_id="text__1",
			value=thread_id
		)
		if results.get('error_message'):
			raise MondayAPIError(results['error_message'])

		if len(results['data']['items_page_by_column_values']['items']) == 1:
			obj = cls(results['data']['items_page_by_column_values']['items'][0]['id']).load_from_api()
			obj.load_from_api()
			return obj
		else:
			raise MondayAPIError(f"Too Many Thread Items ({len(results['data']['items_page_by_column_values']['items'])}) with thread_id {thread_id}")

	def __init__(self, item_id=None, api_data: dict = None, search=False, cache_data=None):
		self.thread_id = columns.TextValue('text__1')
		self.message_ts = columns.TextValue('text1__1')
		self.slack_user_id = columns.TextValue('text3__1')
		self.running_cost = columns.NumberValue('numbers__1')
		super().__init__(item_id, api_data, search, cache_data)
