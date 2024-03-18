import os
import html
import re
import json

from .. import monday
from ...errors import EricError


def format_url(imei, service_number="30", _format="JSON"):
	api_key = os.environ['SICKW_API_KEY']

	return f"https://sickw.com/api.php?format={_format}&key={api_key}&imei={imei}&service={service_number}"


def parse_result_to_dict(sickw_result):
	# Replace <br> tags with a newline character
	cleaned_html = sickw_result.replace('<br>', '\n')

	# Remove any remaining HTML tags and convert HTML entities to plain text
	cleaned_html = re.sub('<.*?>', '', cleaned_html)
	plain_text = html.unescape(cleaned_html)

	# Split the string into lines
	lines = plain_text.split('\n')

	# Function to split lines into key-value pairs, assuming the first colon is the delimiter
	def parse_line(line):
		parts = line.split(': ', 1)  # Only split on the first colon
		if len(parts) == 2:
			return parts[0].strip(), parts[1].strip()
		return None  # Return None for lines that do not contain a key-value pair

	# Create the resulting dictionary by parsing each line and filtering out None values
	info_dict = dict(filter(None, (parse_line(line) for line in lines)))

	return info_dict


def record_device_information(device_data_dict, name: str = ""):
	try:
		# extract and construct initial data
		imei = device_data_dict.get('IMEI')
		serial = device_data_dict.get("Serial Number")

		if not imei and not serial:
			raise ValueError(f"No IMEI or SN (Should be impossible): {device_data_dict}")

		imei_check_board = monday.api.boards.get_board(5808954740)

		model = device_data_dict.get('Model')
		if not name:
			name = f"{model or 'No Model Data'}: {imei or serial}"

		record = monday.items.misc.SickWDataItem()
		record.fetched_data = json.dumps(device_data_dict)

		model_description = device_data_dict.get("Model Description")

		if model:
			record.model = model
		if imei:
			record.imei = imei
		if serial:
			record.serial = serial
		if model_description:
			record.model_description = model_description

		# # check for matching 'model' field
		# model_search = imei_check_board.get_column_value(id='text0')
		# model_search.text = model_search.value = model
		# model_match_items = imei_check_board.get_items_by_column_values(column_value=model_search)
		# if model_match_items:
		# 	record.model_match_connect = [int(item.id) for item in model_match_items]
		#
		# # check for matching 'model description' field
		# model_desc_search = imei_check_board.get_column_value(id='text5')
		# model_desc_search.text = model_desc_search.value = model_description
		# description_match_items = imei_check_board.get_items_by_column_values(column_value=model_desc_search)
		# if description_match_items:
		# 	record.model_description_connect = [int(item.id) for item in description_match_items]

		record.create(name)
		return record
	except Exception as e:
		raise EricError(f"Error while recording IMEI check data: {str(e)}")

