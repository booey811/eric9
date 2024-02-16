import os

from notion_client import Client

notion_client = Client(auth=os.environ["NOTION_API_KEY"])