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
