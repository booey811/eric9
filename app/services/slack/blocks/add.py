from . import elements


def input_block(block_title, element, dispatch_action=False, block_id="", hint="", optional=False, initial_option=None):
	basic = {
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
	if initial_option:
		basic['element']['initial_option'] = initial_option
	return basic


def section_block(block_title, accessory, block_id="", dispatch_action=False, hint="", optional=False):
	return {
		"type": "input",
		"accessory": accessory,
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
