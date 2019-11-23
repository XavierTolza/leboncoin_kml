import re
from os import system

import numpy as np
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.options import Options
from user_agent import generate_user_agent

from leboncoin_kml.common import timeout_settings
from leboncoin_kml.log import LoggingClass
from leboncoin_kml.proxy import PBrocker


class ConnexionError(Exception):
    def __init__(self, e):
        err = str(e)
        r = re.compile(".+about:neterror\?e=([^&]+)&.+")
        _err = r.match(err)
        if _err is not None:
            err = _err.groups()[0]
        super(ConnexionError, self).__init__(err)


class FindProxyError(Exception):
    def __init__(self):
        super(FindProxyError, self).__init__("Unable to find proxy. Are you connected to internet? "
                                             "Is proxybrocker installed?")


class Firefox(webdriver.Firefox, LoggingClass):
    pref_types = {str: "String", int: "Int", bool: "Bool"}
    ip_finder = re.compile(".+[^\d](\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,6}).+")

    def __init__(self, headless=False, timeout=10, enable_cache=False, use_proxy_broker=True):
        self.use_proxy_broker = use_proxy_broker
        options = Options()
        options.headless = headless
        self.timeout = timeout
        preferences = {i: timeout for i in timeout_settings}
        preferences.update({i: enable_cache for i in "browser.cache.disk.enable,browser.cache.memory."
                                                     "enable,browser.cache.offline.enable," \
                                                     "network.http.use-cache".split(",")})
        if use_proxy_broker:
            self.broker = PBrocker()
        LoggingClass.__init__(self)
        if headless:
            fp = webdriver.FirefoxProfile()
            fp.set_preference("http.response.timeout", timeout)
            fp.set_preference("dom.max_script_run_time", timeout)
        else:
            fp = None
        webdriver.Firefox.__init__(self, options=options, firefox_profile=fp)
        self.set_preference(**preferences)

    def new_tab(self, url=None, **kwargs):
        self.execute_script(f'window.open("","_blank");')
        self.tab = -1
        if url is not None:
            self.get(url, **kwargs)
        pass

    @property
    def tab(self):
        comp = np.array([self.current_window_handle]).ravel()[:, None] == np.ravel([self.window_handles])[None, :]
        res = np.argmax(np.ravel(comp))
        return res

    @tab.setter
    def tab(self, value):
        self.switch_to.window(self.window_handles[int(value)])

    def close_tab(self):
        self.execute_script(f'window.close();')
        self.switch_to.window(self.window_handles[-1])

    @property
    def n_tabs(self):
        return len(self.window_handles)

    def __enter__(self):
        if self.use_proxy_broker:
            self.broker.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log.debug("Stopping scrapper")
        if self.use_proxy_broker:
            system(f"kill -9 {self.broker.pid}")
        while len(self.window_handles) > 1:
            self.tab = -1
            self.close_tab()
        self.close()

    def close(self):
        while self.n_tabs > 1:
            self.tab = -1
            self.close_tab()
        super(Firefox, self).close()

    def set_preference(self, **elements):
        self.debug(f"Setting preferences: {elements}")
        self.new_tab("about:config", secure=False)

        try:
            script = """
            var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefBranch);
            prefs.set%sPref(arguments[0], arguments[1]);
            """

            # self.find_element_by_id("warningButton").click()
            # searchbar = self.find_element_by_id("textbox").find_element_by_css_selector("input")
            for key, value in elements.items():
                value_type = type(value)
                # if searchbar is not None:
                #     searchbar.clear()
                #     searchbar.send_keys(key)
                self.execute_script(script % self.pref_types[value_type], key, value)
        except KeyError:
            raise ValueError(f"Wrong type for pref {key} value: {str(value_type)}. Supported types are "
                             f"{list(self.pref_types.keys())}")
        finally:
            self.close_tab()
        return

    def disable_image_load(self):
        self.set_preference(**{"permissions.default.image": 0})
        # "dom.ipc.plugins.enabled.libflashplayer.so": False})

    def set_proxy(self, **kwargs):

        script = ["Services.prefs.setIntPref('network.proxy.type', 1);"]
        values = []
        for i, (k, v) in enumerate(kwargs.items()):
            script.append(f'Services.prefs.setCharPref("network.proxy.{k}", arguments[{i * 2}]);')
            values.append(v[0])
            script.append(f'Services.prefs.setIntPref("network.proxy.{k}_port", arguments[{i * 2 + 1}]);')
            values.append(v[1])
        script = "\n".join(script)

        self.new_tab("about:config")
        self.execute("SET_CONTEXT", {"context": "chrome"})
        try:
            self.execute_script(script, *values)

        finally:
            self.execute("SET_CONTEXT", {"context": "content"})
            self.close_tab()
        pass

    def enable_js(self):
        self.set_preference(**{"javascript.enabled": True})

    def disable_js(self):
        self.set_preference(**{"javascript.enabled": False})

    def get(self, url):
        try:
            super(Firefox, self).get(url)
        except WebDriverException as e:
            raise ConnexionError(e)

    def refresh(self):
        try:
            super(Firefox, self).refresh()
        except WebDriverException as e:
            raise ConnexionError(e)

    def set_user_agent(self, value):
        self.set_preference(**{"general.useragent.override": value})

    def generate_user_agent(self, **kwargs):
        return generate_user_agent(**kwargs)

    def generate_proxy(self):
        queue = self.broker.data
        res = queue.get(timeout=self.timeout)
        return res

    def change_identity(self, proxy=True, user_agent=True):
        if proxy:
            proxy = self.generate_proxy()
            self.set_proxy(http=proxy, ssl=proxy)
        if user_agent:
            self.set_user_agent(self.generate_user_agent())


if __name__ == '__main__':
    f = Firefox()
    f.new_tab("https://google.com")
    p = ("47.254.173.77", 3128)
    f.set_proxy(http=p, ssl=p)
    f.get("https://www.hostip.fr/")
    with f.broker:
        f.change_identity()
        f.change_identity()
        f.change_identity()
    pass
