import re
import subprocess

from selenium import webdriver
import numpy as np
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from user_agent import generate_user_agent


class ProxyError(Exception):
    pass


class Firefox(webdriver.Firefox):
    pref_types = {str: "String", int: "Int", bool: "Bool"}
    ip_finder = re.compile(".+[^\d](\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,6}).+")

    def __init__(self, headless=False):
        options = Options()
        options.headless = headless
        super(Firefox, self).__init__(options=options)
        # profile = FirefoxProfile()
        # profile.set_preference("network.proxy.type", 1)
        # profile.set_preference("network.proxy.socks", "localhost")
        # profile.set_preference("network.proxy.socks_port", 9050)
        # profile.set_preference("network.proxy.http", "localhost")
        # profile.set_preference("network.proxy.http_port", 8888)
        # profile.set_preference("network.proxy.https", "localhost")
        # profile.set_preference("network.proxy.https_port", 8888)
        # profile.set_preference("network.proxy.share_proxy_settings", True)
        # profile.set_preference("javascript.enabled", False)
        # profile.update_preferences()

    def new_tab(self, url=None):
        self.execute_script(f'window.open("","_blank");')
        self.tab = -1
        if url is not None:
            self.get(url)
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
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        while self.n_tabs > 1:
            self.tab = -1
            self.close_tab()
        super(Firefox, self).close()

    def set_preference(self, **elements):
        self.new_tab("about:config")

        try:
            script = """
            var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefBranch);
            prefs.set%sPref(arguments[0], arguments[1]);
            """

            searchbar = None
            try:
                self.find_element_by_id("warningButton").click()
                searchbar = self.find_element_by_id("textbox").find_element_by_css_selector("input")
            finally:
                for key, value in elements.items():
                    value_type = type(value)
                    if searchbar is not None:
                        searchbar.clear()
                        searchbar.send_keys(key)
                    self.execute_script(script % self.pref_types[value_type], key, value)
        except KeyError:
            raise ValueError(f"Wrong type for pref {key} value: {str(value_type)}. Supported types are "
                             f"{list(self.pref_types.keys())}")
        finally:
            self.close_tab()

    def set_proxy(self, type=1, share_proxy_settings=False, **proxies):
        pref = {"network.proxy.type": type, "network.proxy.share_proxy_settings": share_proxy_settings}
        for name, (addr, port) in proxies.items():
            pref.update({f"network.proxy.{name}": addr, f"network.proxy.{name}_port": port})
        self.set_preference(**pref)

    def enable_js(self):
        self.set_preference(**{"javascript.enabled": True})

    def disable_js(self):
        self.set_preference(**{"javascript.enabled": False})

    def get(self, url):
        try:
            super(Firefox, self).get(url)
        except WebDriverException as e:
            if "about:neterror?e=proxyConnectFailure" in str(e):
                raise ProxyError("Proxy connexion refused. Are your proxy settings correct?")
            raise

    def set_user_agent(self, value):
        self.set_preference(**{"general.useragent.overridepreference": value})

    def generate_user_agent(self, **kwargs):
        return generate_user_agent(**kwargs)

    def generate_proxy(self):
        cmd = "proxybroker find --types SOCKS5 --strict -l 1"
        res = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE)
        res = res.stdout
        res = self.ip_finder.match(res.decode("utf-8")).groups()[0]
        res = list(res.split(":"))
        res[1] = int(res[1])
        return res

    def change_identity(self):
        self.set_proxy(socks=self.generate_proxy())
        self.set_user_agent(self.generate_user_agent())


if __name__ == '__main__':
    with Firefox() as f:
        f.change_identity()
        f.get("https://webkay.robinlinus.com/")
        pass
