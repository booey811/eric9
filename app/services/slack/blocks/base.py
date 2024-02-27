def get_modal_base(title, submit="Submit", cancel="Cancel", callback_id=""):
	basic = {
		"type": "modal",
		"title": {
			"type": "plain_text",
			"text": title,
			"emoji": True
		},
		"close": {
			"type": "plain_text",
			"text": cancel,
			"emoji": True
		},
		"blocks": []
	}

	if submit:
		basic["submit"] = {
			"type": "plain_text",
			"text": submit,
			"emoji": True
		}

	if cancel:
		basic["close"] = {
			"type": "plain_text",
			"text": cancel,
			"emoji": True
		}

	if callback_id:
		basic["callback_id"] = callback_id

	return basic
