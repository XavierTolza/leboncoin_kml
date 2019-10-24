from datetime import datetime, timedelta
from time import sleep, time

from selenium.common.exceptions import NoSuchElementException

from leboncoin_kml.common import months


class FinalPageReached(Exception):
    pass


class LBC(object):
    def __init__(self, driver, url):
        self.url = url
        self.driver = driver

    def __enter__(self):
        self.driver.get(self.url)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()

    @property
    def blocked(self):
        return "blocked" in self.driver.title

    @property
    def next_page_link(self):
        return self.driver.find_element_by_css_selector("nav div ul").find_elements_by_css_selector("li")[-1] \
            .find_element_by_css_selector('a')

    def got_to_next_page(self):
        try:
            link = self.next_page_link
            url = link.get_attribute("href")
            self.driver.get(url)
        except NoSuchElementException:
            raise FinalPageReached()

    @property
    def list(self):
        res = self.driver.find_elements_by_css_selector("ul")[0].find_elements_by_css_selector("li")
        res = [Annonce(self.driver, i) for i in res if len(i.text) and not "annonce sponsorisée" in i.text.lower()]
        return res


class Annonce(object):
    def __init__(self, driver, element):
        self.driver = driver
        self.element = element

    @property
    def title(self):
        return self.element.find_element_by_css_selector("section div p span").text

    @property
    def url(self):
        return self.element.find_element_by_css_selector("a").get_attribute("href")

    @property
    def price(self):
        res = int(self.element.find_element_by_css_selector(
            "section div div span span[itemprop=\"priceCurrency\"]").get_attribute("innerHTML").split("-->")[1].split(
            "<!--")[0].replace(" ", ""))
        return res

    @property
    def at(self):
        res = self.element.find_element_by_css_selector('section div p[itemprop="availableAtOrFrom"]').text
        return res

    @property
    def post_date(self):
        res = self.element.find_element_by_css_selector('section div p[itemprop="availabilityStarts"]').text
        day, hour = res.lower().split(", ")
        hour, min = [int(i) for i in hour.split(":")]
        now = datetime.today()
        if "hier" in day:
            now = now - timedelta(days=1)
        elif "aujourd" in day:
            now = datetime(now.year, now.month, now.day, hour, min, 0, 0)
        else:
            day, month = day.split(" ")
            try:
                month = months[month]
            except KeyError:
                raise KeyError("Invalid month detected: you should add %s in common.py" % month)
            now = datetime(now.year, month, int(day), hour, min, 0, 0)

        return now.timestamp()

    @property
    def img_url(self):
        tic = time()
        res = None
        while res is None and (time() - tic) < 5:
            try:
                res = self.element.find_element_by_css_selector('a div span div img').get_attribute("src")
            except Exception:
                self.scroll_view()
                sleep(1)
        return res

    def __dict__(self):
        return dict(export_time=time(),
                    url=self.url,
                    img=self.img_url,
                    post_date=self.post_date,
                    address=self.at,
                    price=self.price,
                    title=self.title)

    @property
    def dict(self):
        return self.__dict__()

    def scroll_view(self):
        self.driver.execute_script("arguments[0].scrollIntoView();", self.element)
