

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
