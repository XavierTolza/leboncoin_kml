from selenium import webdriver
import numpy as np
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options


class Firefox(webdriver.Firefox):
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
            prefs.setBoolPref(arguments[0], arguments[1]);
            """

            try:
                self.find_element_by_id("warningButton").click()
            finally:
                for key, value in elements.items():
                    self.find_element_by_id("textbox").find_element_by_css_selector("input").send_keys(key)
                    self.execute_script(script, key, value)
        finally:
            self.close_tab()

    def set_proxy(self, type=1, **proxies):
        pref = {"network.proxy.type": type}
        for name, (addr, port) in proxies.items():
            pref.update({f"network.proxy.{name}": addr, f"network.proxy.{name}_port": port})
        self.set_preference(**pref)

    def enable_js(self):
        self.set_preference(**{"javascript.enabled": True})

    def disable_js(self):
        self.set_preference(**{"javascript.enabled": False})


if __name__ == '__main__':
    with Firefox() as f:
        f.new_tab("https://google.com")
        f.new_tab("https://google.com")
        f.new_tab("https://google.com")
        print(f.tab)
        f.tab = 0
        print(f.tab)
        f.tab = 1
        f.close_tab()
        f.disable_js()
        f.enable_js()
        f.set_proxy(sock=("localhost", 9095))
        pass
