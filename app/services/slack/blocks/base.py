def get_modal_base(title, submit="Submit", cancel="Cancel"):
	return {
		"view": {
			"type": "modal",
			"title": {
				"type": "plain_text",
				"text": title,
				"emoji": True
			},
			"submit": {
				"type": "plain_text",
				"text": submit,
				"emoji": True
			},
			"close": {
				"type": "plain_text",
				"text": cancel,
				"emoji": True
			},
			"blocks": []
		}
	}
