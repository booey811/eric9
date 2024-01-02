def generate_option(text, value):
	return {
		"text": {
			"type": "plain_text",
			"text": text
		},
		"value": value
	}


def generate_option_groups(options_dict):
	"""
	:param options_dict: dictionary containing a group title key with list of lists (text-value pairs) values to use
	:type options_dict: dict
	:return: dictionary of option groups with options
	:rtype: dict
	"""
	final = {"option_groups": []}
	for group_title in options_dict:
		inner = {
			"label": {
				"type": "plain_text",
				"text": group_title
			},
			"options": []
		}

		for text_value_pair in options_dict[group_title]:
			inner['options'].append(generate_option(text_value_pair[0], text_value_pair[1]))

		final['option_groups'].append(inner)
	return final
