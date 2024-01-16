from . import elements


def input_block(block_title, element, dispatch_action=False, block_id="", hint="", optional=False):
	return {
		"type": "input",
		"element": element,
		"label": {
			"type": "plain_text",
			"text": block_title,
			"emoji": True
		},
		"dispatch_action": dispatch_action,
		"block_id": block_id,
		"hint": hint,
		"optional": optional
	}


def text_block(content):
	return {
		"type": "rich_text",
		"elements": [elements.text_element(content)]
	}
