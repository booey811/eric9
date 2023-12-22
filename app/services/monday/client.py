import os

import moncli

moncli.api.api_key = os.environ['MON_SYSTEM']

client = moncli.client
