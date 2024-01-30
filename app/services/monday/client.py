import os

import moncli

from app import config

conf = config.get_config()

moncli.api.api_key = conf.MONDAY_KEYS["system"]
moncli.api.connection_timeout = 30

client = moncli.client
