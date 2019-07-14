import logging

import urllib3

logging.getLogger("urllib3").setLevel(logging.WARNING)

headers = {
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0'
}
http = urllib3.PoolManager(headers=headers)

get = lambda *args, **kwargs: http.request("GET", *args, **kwargs)
