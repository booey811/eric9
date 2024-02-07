import json

from .client import client


def get_col_defs(client, board_id):
	data = client.boards.fetch_boards_by_id([board_id])
	columns = data['data']['boards'][0]['columns']
	col_defs = {}
	for column in columns:
		col_defs[column['id']] = column
	return col_defs


def get_formatted_value(col_defs, field_name, value):
	""" Take a cell and make it human readable. """

	def format_default(col_defs, field_name, value):
		return value

	def format_text_field(col_defs, field_name, value):
		return json.loads(value)

	def format_date_field(col_defs, field_name, value):
		if value is None:
			return ''
		return json.loads(value)['date']

	def format_numeric_field(col_defs, field_name, value):
		if value is None:
			return ''
		return json.loads(value)

	def format_longtext_field(col_defs, field_name, value):
		if value is None:
			return ''
		value = json.loads(value)['text']
		return value.strip() if value else ''

	def format_color_field(col_defs, field_name, value):
		if value is None:
			return ''
		labels = json.loads(col_defs[field_name]['settings_str'])['labels']
		return labels.get(str(json.loads(value)['index']))

	def format_dropdown_field(col_defs, field_name, value):
		if value is None:
			return ''
		labels = json.loads(col_defs[field_name]['settings_str'])['labels']
		label_map = dict([(row['id'], row['name']) for row in labels])
		return ", ".join([label_map.get(id) for id in json.loads(value)['ids']])

	type_to_callable_map = {
		'color': format_color_field,
		'dropdown': format_dropdown_field,
		'long-text': format_longtext_field,
		'date': format_date_field,
		'numeric': format_numeric_field,
		'text': format_text_field,
	}
	t = col_defs[field_name]['type']
	formatter = type_to_callable_map.get(t, format_default)
	return formatter(col_defs, field_name, value)


# Connect to Monday
conn = client

# Grab a map of column IDs and their settings
col_defs = get_col_defs(conn, 349212843)

# Grab all the rows (items) from a board
data = conn.boards.fetch_items_by_board_id([349212843])

# Loop through each cell and format it according to the cell settings
rows = []
for item in data['data']['boards'][0]['items']:
	row = {}
	for col in item['column_values']:
		row.append(get_formatted_value(col_defs, col['id'], col['value']))
	rows.append(row)

# Use e.g. tablib to format for console.
ds = tablib.Dataset()
ds.dict = rows
print(ds.tsv)
