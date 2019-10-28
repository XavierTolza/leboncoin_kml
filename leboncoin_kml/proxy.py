import asyncio
from multiprocessing import Process, Queue

import numpy as np
from proxybroker import Broker

from leboncoin_kml.log import LoggingClass


class PBrocker(Process, LoggingClass):
    def __init__(self):
        Process.__init__(self)
        LoggingClass.__init__(self)
        self.data = Queue()
        self.proxies = proxies = asyncio.Queue()
        self.brocker = Broker(proxies)
        self.loop = asyncio.get_event_loop()

    def run(self) -> None:
        self.debug("Starting loop")
        tasks = asyncio.gather(
            self.brocker.find(types=['HTTP', 'HTTPS'], limit=np.inf),
            self.save(),
        )
        self.loop.run_until_complete(tasks)
        self.debug("Finished run")

    async def save(self):
        """Save proxies to a file."""
        while True:
            proxy = await self.proxies.get()
            if proxy is None:
                break
            proxy = (proxy.host, proxy.port)
            self.append(proxy)

    def append(self, value):
        self.log.debug(f"Found new proxy: {value}. Queue has size {self.data.qsize()}")
        self.data.put(value)

    def stop(self):
        self.log.debug("Stopping brocker")
        self.brocker.stop()
        self.__stopped = True

    def start(self) -> None:
        super(PBrocker, self).start()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.debug(f"Joining")
        self.join()
