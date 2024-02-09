from ..api import items, columns


class MainItem(items.BaseItemType):
	BOARD_ID = 349212843

	# basic info
	main_status = columns.StatusValue("status4")

	# repair info
	products_connect = columns.ConnectBoards("board_relation")
	description = columns.TextValue("text368")

	# tech info
	technician_id = columns.PeopleValue("person")

	# scheduling info
	motion_task_id = columns.TextValue("text76")
	motion_scheduling_status = columns.StatusValue("status_19")
	hard_deadline = columns.DateValue("date36")
	phase_deadline = columns.DateValue("date65")


class PropertyTestItem(items.BaseItemType):
	BOARD_ID = 349212843

	text = columns.TextValue('text69')
	number = columns.NumberValue('dup__of_quote_total')
	status = columns.StatusValue('status_161')
	date = columns.DateValue('date6')
	url_link = columns.LinkURLValue('link1')
	product_connect = columns.ConnectBoards('board_relation')
	long_text = columns.LongTextValue("long_text5")
	people = columns.PeopleValue('person')
	dropdown = columns.DropdownValue("device0")
