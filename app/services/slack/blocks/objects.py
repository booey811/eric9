def text_object(content):
	return {
		"type": "mrkdwn",
		"text": str(content)
	}


def generate_option(text, value):
	return {
		"text": text,
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
			option = {
				"text": {
					"type": "plain_text",
					"text": text_value_pair[0]
				},
				"value": text_value_pair[1]
			}
			inner["options"].append(option)

		final.append(inner)
	return final
