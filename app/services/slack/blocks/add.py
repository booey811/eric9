from . import elements


def input_block(block_title, element, dispatch_action=False, block_id="", hint="", optional=False, initial_option=[], action_id=''):
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
		"optional": optional
	}
	if initial_option:
		basic['element']['initial_option'] = {"text": {'type': 'plain_text', 'text': initial_option[0]}, "value": initial_option[1]}
	if hint:
		basic['hint'] = {
			"type": "plain_text",
			"text": hint,
			"emoji": True
		}
	if dispatch_action and not action_id:
		raise ValueError("dispatch_action requires an action_id")
	elif dispatch_action:
		basic['element']['action_id'] = action_id
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


def rich_text_block(list_of_elements, block_id=''):
	basic = {
		"type": "rich_text",
		"block_id": block_id,
		"elements": list_of_elements
	}

	return basic
