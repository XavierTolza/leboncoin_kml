from selenium.common.exceptions import NoSuchElementException

from leboncoin_kml.scrapper import Firefox


class FinalPageReached(Exception):
    pass


class ParserBlocked(Exception):
    pass


class WrongUserAgent(Exception):
    pass



class LBC(Firefox):
    def __init__(self, url, headless=False, start_anonymously=False):
        super(LBC, self).__init__(headless=headless)
        self.start_anonymously = start_anonymously
        self.url = url
        self.__current_url = url

    def __enter__(self):
        super(LBC, self).__enter__()
        if self.start_anonymously:
            self.change_identity()
        self.get(self.url)
        return self

    @property
    def blocked(self):
        return "blocked" in self.title

    @property
    def next_page_link(self):
        res = self.find_element_by_name("chevronright").find_element_by_xpath("./..")
        return res

    def got_to_next_page(self):
        try:
            link = self.next_page_link
            url = link.get_attribute("href")
            self.get(url)
            self.__current_url = url
        except NoSuchElementException:
            raise FinalPageReached()

    @property
    def list(self):
        data = self.execute_script("return window.__REDIAL_PROPS__;")
        res = data[4]["data"]["ads"]
        return res

    def set_proxy(self, *args, **kwargs):
        super(LBC, self).set_proxy(*args, **kwargs)
        self.log.info(f"Setting proxy {(args, kwargs)}")

    def set_user_agent(self, value):
        super(LBC, self).set_user_agent(value)
        self.log.info(f"Setting user agent: {value}")

    def refresh(self):
        url = self.__current_url
        self.get(url)
