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
import asyncio
import re
import random
import base64
import logging
from asyncio import sleep
from queue import Queue
from threading import Thread
from urllib.parse import urlparse

import aiohttp
from proxybroker import ProxyPool, Broker
from proxybroker.errors import NoProxyError

log = logging.getLogger('scrapy.proxies')


class Mode:
    RANDOMIZE_PROXY_EVERY_REQUESTS, RANDOMIZE_PROXY_ONCE, SET_CUSTOM_PROXY = range(3)


class ProxyQueue(Thread):
    def __init__(self, n_items=10):
        super(ProxyQueue, self).__init__()
        self.queue = Queue(n_items)
        self.stop = False

    async def fetch(self, url, proxy_pool, timeout, loop):
        resp, proxy = None, None
        while self.queue.full():
            await sleep(5)
        if self.stop:
            return
        try:
            proxy = await proxy_pool.get(scheme=urlparse(url).scheme)
            proxy_url = 'http://%s:%d' % (proxy.host, proxy.port)
            _timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(
                    timeout=_timeout, loop=loop
            ) as session, session.get(url, proxy=proxy_url) as response:
                resp = await response.text()
        except (
                aiohttp.errors.ClientOSError,
                aiohttp.errors.ClientResponseError,
                aiohttp.errors.ServerDisconnectedError,
                asyncio.TimeoutError,
                NoProxyError,
        ) as e:
            print('Error!\nURL: %s;\nError: %r\n', url, e)
        finally:
            if proxy:
                proxy_pool.put(proxy)
                self.queue.put()
            return (url, resp)

    async def get_pages(self, urls, proxy_pool, timeout=10, loop=None):
        tasks = [self.fetch(url, proxy_pool, timeout, loop) for url in urls]
        for task in asyncio.as_completed(tasks):
            url, content = await task
            print('%s\nDone!\nURL: %s;\nContent: %s' % ('-' * 20, url, content))

    def run(self) -> None:
        loop = asyncio.new_event_loop()

        proxies = asyncio.Queue(loop=loop)
        proxy_pool = ProxyPool(proxies)

        judges = [
            'http://httpbin.org/get?show_env',
            'https://httpbin.org/get?show_env',
        ]

        providers = [
            'http://www.proxylists.net/',
            'http://ipaddress.com/proxy-list/',
            'https://www.sslproxies.org/',
        ]

        broker = Broker(
            proxies,
            timeout=8,
            max_conn=200,
            max_tries=3,
            verify_ssl=False,
            judges=judges,
            providers=providers,
            loop=loop,
        )

        types = [('HTTP', ('Anonymous', 'High'))]
        countries = ['US', 'UK', 'DE', 'FR']

        urls = [
            'http://httpbin.org/get',
            'http://httpbin.org/redirect/1',
            'http://httpbin.org/anything',
            'http://httpbin.org/status/404',
        ]

        tasks = asyncio.gather(
            broker.find(types=types, countries=countries, strict=True, limit=10),
            self.get_pages(urls, proxy_pool, loop=loop),
        )
        loop.run_until_complete(tasks)


class RandomProxy(object):
    def __init__(self, settings):
        self.mode = settings.get('PROXY_MODE')
        self.proxy_finder = pf = ProxyQueue()
        pf.start()
        while pf.queue.empty():
            sleep(1)

        self.chosen_proxy = ''

        if self.mode == Mode.SET_CUSTOM_PROXY:
            custom_proxy = settings.get('CUSTOM_PROXY')
            self.proxies = {}
            parts = re.match('(\w+://)([^:]+?:[^@]+?@)?(.+)', custom_proxy.strip())
            if not parts:
                raise ValueError('CUSTOM_PROXY is not well formatted')

            if parts.group(2):
                user_pass = parts.group(2)[:-1]
            else:
                user_pass = ''

            self.proxies[parts.group(1) + parts.group(3)] = user_pass
            self.chosen_proxy = parts.group(1) + parts.group(3)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # Don't overwrite with a random one (server-side state for IP)
        if 'proxy' in request.meta:
            if request.meta["exception"] is False:
                return
        request.meta["exception"] = False

        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or len(self.chosen_proxy) == 0:
            if self.proxy_finder.queue.empty():
                raise ValueError('All proxies are unusable, cannot proceed')
            self.chosen_proxy = proxy_address = self.proxy_finder.queue.get()
        else:
            proxy_address = self.chosen_proxy

        request.meta['proxy'] = proxy_address
        log.debug('Using proxy <%s>' % (proxy_address))

    def process_exception(self, request, exception, spider):
        if 'proxy' not in request.meta:
            return
        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            proxy = request.meta['proxy']
            try:
                del self.proxies[proxy]
            except KeyError:
                pass
            request.meta["exception"] = True
            if self.mode == Mode.RANDOMIZE_PROXY_ONCE:
                self.chosen_proxy = random.choice(list(self.proxies.keys()))
            log.info('Removing failed proxy <%s>, %d proxies left' % (
                proxy, len(self.proxies)))
