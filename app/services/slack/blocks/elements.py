def generate_option(text, value):
	return {
		"text": {
			"type": "plain_text",
			"text": str(text)
		},
		"value": str(value)
	}


def generate_option_groups(options_dict):
	"""
	:param options_dict: dictionary containing a group title key with list of lists (text-value pairs) values to use
	:type options_dict: dict
	:return: dictionary of option groups with options
	:rtype: dict
	"""
	final = []
	for group_title in options_dict:
		inner = {
			"label": {
				"type": "plain_text",
				"text": str(group_title)
			},
			"options": []
		}

		for text_value_pair in options_dict[group_title]:
			inner['options'].append(generate_option(text_value_pair[0], text_value_pair[1]))

		final.append(inner)
	return final


def text_element(content):
	return {
		"type": "rich_text_section",
		"elements": [
			{
				"type": "text",
				"text": content
			}
		]
	}