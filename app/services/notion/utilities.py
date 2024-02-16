from pprint import pprint as p

from .client import notion_client


def get_page_text(page_id):

	TEST_PAGE_ID = "716462ae-b27e-4f6e-b5a4-446c92871eb7"
	content_query = notion_client.blocks.children.list(TEST_PAGE_ID)

	text = ""

	for child in content_query['results']:
		p("====== CHILD ======")
		p(child)
		block_type = child['type']
		if block_type in ('table_of_contents', 'unsupported'):
			continue
		for line in child[block_type]['rich_text']:
			p("====== LINE ======")
			p(line)
			try:
				text += line['plain_text']
			except KeyError:
				line_type = line['type']
				if line_type in ('mention', 'table_of_contents', 'equation', 'divider', 'page', 'unsupported'):
					continue
				line_content = line[line_type]
				p("====== LINE CONTENT ======")
				p(line_content)
				text += line[line_type]['content']

	return text



