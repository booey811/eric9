import os

import moncli

from ... import conf

moncli.api.api_key = conf.MONDAY_KEYS["system"]

client = moncli.client
