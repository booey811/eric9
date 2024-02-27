def external_select_element(action_id, placeholder, min_query_length=3):
	return {
		"action_id": str(action_id),
		"type": "external_select",
		"placeholder": {
			"type": "plain_text",
			"text": placeholder
		},
		"min_query_length": min_query_length
	}


def multi_external_select_element(action_id, placeholder, min_query_length=3):
	return {
		"action_id": str(action_id),
		"type": "multi_external_select",
		"placeholder": {
			"type": "plain_text",
			"text": placeholder
		},
		"min_query_length": min_query_length
	}


def static_select_element(action_id, placeholder, options=(), option_groups=()):
	basic = {
		"action_id": str(action_id),
		"type": "static_select",
		"placeholder": {
			"type": "plain_text",
			"text": placeholder
		},
	}

	if not options and not option_groups:
		raise ValueError("options or option_groups must be provided")
	elif options:
		basic["options"] = options
	elif option_groups:
		basic["option_groups"] = option_groups
	else:
		raise ValueError("options or option_groups must be provided")

	return basic


def rich_text_elements(list_of_content):
	assert isinstance(list_of_content, list), "list_of_content must be a list of dictionaries"

	def make_element(text):
		return {
			"type": "text",
			"text": text
		}

	basic = {
		"type": "rich_text_section",
		"elements": [make_element(_) for _ in list_of_content]
	}

	return [basic]


def text_element(content):
	return {
		"type": "mrkdwn",
		"text": str(content)
	}


def overflow_accessory(action_id, options):

	basic = {
		"type": "overflow",
		"options": options,
		"action_id": action_id
	}

	return basic


def text_input_element(placeholder='', action_id='', multiline=False, initial_value=''):
	basic = {
		"type": "plain_text_input",
		"action_id": action_id,
		"multiline": multiline
	}
	if placeholder:
		basic['placeholder'] = {
			"type": "plain_text",
			"text": placeholder
		}
	if initial_value:
		basic['initial_value'] = str(initial_value)
	return basic