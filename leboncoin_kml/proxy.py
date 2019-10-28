import asyncio
from multiprocessing import Process, Queue
from time import sleep

import numpy as np
from proxybroker import Broker

from leboncoin_kml.log import LoggingClass


async def save(proxies, self):
    """Save proxies to a file."""
    while True:
        proxy = await proxies.get()
        if proxy is None:
            break
        proxy = (proxy.host, proxy.port)
        while self.data.qsize() > 100 and self.running:
            sleep(5)
        self.append(proxy)


class PBrocker(Process, LoggingClass):
    def __init__(self):
        Process.__init__(self)
        LoggingClass.__init__(self)
        self.data = Queue()
        self.proxies = proxies = asyncio.Queue()
        self.__brocker = Broker(proxies)
        self.loop = asyncio.get_event_loop()
        self.running = False

    def run(self) -> None:
        tasks = asyncio.gather(
            self.__brocker.find(types=['HTTP', 'HTTPS'], limit=np.inf),
            save(self.proxies, self),
        )
        self.loop.run_until_complete(tasks)

    def append(self, value):
        self.log.info(f"Found new proxy: {value}. Queue has size {self.data.qsize()}")
        self.data.put(value)

    def stop(self):
        self.log.debug("Stopping brocker")
        self.running = False
        self.__brocker.stop()
        self.loop.stop()

    def start(self) -> None:
        self.running = True
        super(PBrocker, self).start()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.join()
