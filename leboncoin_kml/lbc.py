from json import dump
from time import sleep, time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


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
        return self.element.find_element_by_css_selector('section div p[itemprop="availableAtOrFrom"]').text

    @property
    def post_date(self):
        return self.element.find_element_by_css_selector('section div p[itemprop="availabilityStarts"]').text

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


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"

    with open("output.txt", "w") as fp:
        with LBC(webdriver.Firefox(), url) as d:
            try:
                while True:
                    while d.blocked:
                        print("Please solve captcha")
                        sleep(2)
                    sleep(2)
                    print("Getting page info")
                    all = d.list
                    try:
                        print("Parsing page")
                        annonces = [i.dict for i in all]
                        print("Going to next page")
                        d.got_to_next_page()
                    except NoSuchElementException as e:
                        print(str(e))

                    for i in annonces:
                        print(i)
                        dump(i, fp)
            except FinalPageReached:
                print("Finished research")
