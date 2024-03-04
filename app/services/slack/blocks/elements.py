def external_select_element(action_id, placeholder, min_query_length=3, focus_on_load=False):
	basic = {
		"action_id": str(action_id),
		"type": "external_select",
		"placeholder": {
			"type": "plain_text",
			"text": placeholder
		},
		"min_query_length": min_query_length
	}

	if focus_on_load:
		basic['focus_on_load'] = focus_on_load

	return basic


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


def static_select_element(action_id, placeholder, options=(), option_groups=(), focus_on_load=False):
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

	if focus_on_load:
		basic['focus_on_load'] = focus_on_load

	return basic


def multi_select_element(placeholder, action_id='', options=(), option_groups=(), initial_options=()):
	basic = {
		"type": "multi_static_select",
		"placeholder": {
			"type": "plain_text",
			"text": placeholder
		},
	}

	if not options and not option_groups:
		raise ValueError("options or option_groups must be provided")
	elif options:
		basic["options"] = options
		if initial_options:
			basic['initial_options'] = initial_options
	elif option_groups:
		basic["option_groups"] = option_groups
	else:
		raise ValueError("options or option_groups must be provided")

	if action_id:
		basic['action_id'] = action_id

	if initial_options:
		for ds in initial_options:

			if ds not in options:
				raise ValueError(f"Initial option {ds} not in options")

		basic['initial_options']

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
		"multiline": multiline
	}
	if placeholder:
		basic['placeholder'] = {
			"type": "plain_text",
			"text": placeholder
		}
	if initial_value:
		basic['initial_value'] = str(initial_value)
	if action_id:
		basic['action_id'] = action_id
	return basic


def button_element(button_text, button_value='', action_id='', button_style='primary'):
	basic = {
		"type": "button",
		"text": {
			"type": "plain_text",
			"text": button_text
		},
		"style": button_style,
	}
	if button_value:
		basic['value'] = button_value
	if action_id:
		basic['action_id'] = action_id
	return basic


def checkbox_element(options, action_id='', initial_options=()):
	basic = {
		"type": "checkboxes",
		"options": options,
	}
	if action_id:
		basic['action_id'] = action_id
	if initial_options:
		basic['initial_options'] = initial_options
		for ds in initial_options:
			if ds not in options:
				raise ValueError(f"Initial option {ds} not in options: {options}")

	return basic


def radio_button_element(options, action_id='', initial_option=''):
	basic = {
		"type": "radio_buttons",
		"options": options,
	}
	if action_id:
		basic['action_id'] = action_id
	if initial_option:
		basic['initial_option'] = initial_option
		if initial_option not in options:
			raise ValueError(f"Initial option {initial_option} not in options: {options}")

	return basic