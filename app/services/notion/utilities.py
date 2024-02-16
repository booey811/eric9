from pprint import pprint as p

from .client import notion_client


def get_page_text(page_id):

	content_query = notion_client.blocks.children.list(page_id)

	text = ""

	for child in content_query['results']:
		block_type = child['type']
		if block_type in ('table_of_contents', 'unsupported'):
			continue
		for line in child[block_type]['rich_text']:
			try:
				text += line['plain_text']
			except KeyError:
				line_type = line['type']
				if line_type in ('mention', 'table_of_contents', 'equation', 'divider', 'page', 'unsupported'):
					continue
				line_content = line[line_type]
				text += line[line_type]['content']

	return text



