# Copyright (C) 2013 by Aivars Kalvans <aivars.kalvans@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import logging
import random
import re
from multiprocessing import Lock

from scrapy.http import Headers

from leboncoin_kml.common import user_agents, encoding

log = logging.getLogger('scrapy.proxies')
logging.getLogger('proxybroker').setLevel(logging.WARNING)


class Mode:
    RANDOMIZE_PROXY_EVERY_REQUESTS, RANDOMIZE_PROXY_ONCE, SET_CUSTOM_PROXY = range(3)


lock = Lock()


class RandomProxy(object):

    def __init__(self, settings):
        self.settings = settings
        self.mode = settings.get('PROXY_MODE')
        self.remove_failed_proxies = self.settings.get("REMOVE_FAILED_PROXY", False)
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.proxy_list = settings.get('PROXY_LIST')
        self.chosen_proxy = ''
        self.proxies = {}
        self.update_proxies()

    def update_proxies(self):
        log.debug("Updating proxies")
        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            if self.proxy_list is None:
                raise KeyError('PROXY_LIST setting is missing')
            self.proxies = {}
            regex = [
                '.*(https|http)[^\d]+((\d{1,3}\.){3}\d{1,3}:\d{1,6}).*',
                '((\d{1,3}\.){3}\d{1,3}:\d{1,6}).*'
            ]
            with open(self.proxy_list, "r") as fp:
                lines = fp.read().split("\n")
            for line in lines:
                if not len(line): continue
                parts = next(j for j in (re.match(i, line, re.IGNORECASE) for i in regex) if j is not None)
                if not parts:
                    continue
                groups = parts.groups()
                protocol, addr = groups[:2]
                if protocol is None:
                    protocol = "http"
                url = f"{protocol.lower()}://{addr}"

                self.proxies[url] = ''
            if self.mode == Mode.RANDOMIZE_PROXY_ONCE:
                self.chosen_proxy = random.choice(list(self.proxies.keys()))
        elif self.mode == Mode.SET_CUSTOM_PROXY:
            self.chosen_proxy = self.settings.get("PROXY_ADDRESS")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def set_proxy_on_request(self, request, force_change=False):
        with lock:
            if self.mode == Mode.SET_CUSTOM_PROXY:
                proxy_address = self.chosen_proxy
            else:
                if len(self.proxies) == 0:
                    raise ValueError('All proxies are unusable, cannot proceed')

                if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or len(self.chosen_proxy) < 3 or force_change:
                    proxy_address = self.chosen_proxy = random.choice(list(self.proxies.keys()))
                    log.debug('Using proxy <%s>, %d proxies left' % (proxy_address, len(self.proxies)))
                else:
                    proxy_address = self.chosen_proxy
            request.meta['proxy'] = proxy_address
            headers = dict(USER_AGENT=random.choice(user_agents))
            request.headers = Headers(headers, encoding=encoding)

    def process_request(self, request, spider):
        # Don't overwrite with a random one (server-side state for IP)
        if 'proxy' in request.meta:
            if request.meta["exception"] is False:
                return
        request.meta["exception"] = False
        self.set_proxy_on_request(request)

    def process_response(self, request, response, spider):
        status = response.status
        if status == 200:
            return response
        else:
            if (status // 100) == 4:
                # Request failed, resheduling
                newrequest = self.process_exception(request, "Invalid status code: %i" % status, spider)
                return newrequest
            else:
                raise ValueError("Found incorrect error code: %i" % status)

    def export_proxies(self):
        with lock:
            with open(self.proxy_list, "w") as fp:
                for i in self.proxies.keys():
                    fp.write(i + "\n")

    def process_exception(self, request, exception, spider):
        # log.warning("Got error %s for request %s" % (exception, request.url))
        retries = request.meta.get('retry_times', 0)
        max_retry_times = self.max_retry_times

        # Remove failed proxy from list
        if self.remove_failed_proxies and \
                self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            proxy = request.meta['proxy']
            with lock:
                try:
                    del self.proxies[proxy]
                except KeyError:
                    pass
                n_proxies_left = len(self.proxies)
            self.chosen_proxy = ''
            log.info('Removing failed proxy <%s>, %d proxies left' % (
                proxy, n_proxies_left))
            request.meta["exception"] = True

        # Retry with new proxy
        description = request.meta["description"] if "description" in request.meta else ''
        if retries <= max_retry_times:
            log.info(f"Retrying {description} {request} (failed {retries} times): {exception}")
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries + 1
            retryreq.dont_filter = True
            self.set_proxy_on_request(request, force_change=True)
            res = retryreq
        else:
            raise ValueError("Request %s failed too much! (%i times)" % (request.url, max_retry_times))
        return res
