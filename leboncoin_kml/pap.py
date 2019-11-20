from bs4 import BeautifulSoup
from requests import get

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC
from leboncoin_kml.annonce import Annonce as LBCAnnonce


class ConfigPap(Config):
    url = "https://www.pap.fr/annonce/vente-maisons-midi-pyrenees-g475-a-partir-du-3-pieces-jusqu-a-300000-euros-a-partir-de-60-m2"


class Annonce(LBCAnnonce):
    @staticmethod
    def from_element(el):
        url = el.find_element_by_css_selector(".item-title").get_attribute("href")
        page = get(url)
        page = BeautifulSoup(page.text)
        title = el.find_element_by_css_selector("span.h1").text
        price = int(el.find_element_by_css_selector("span.item-price").text.replace(".", "").split(" ")[0])
        images = page.find_all("a.img-liquid")
        res = dict(
            body=el.find_element_by_css_selector(".item-description").text()
        )


class Pap(LBC):
    def __init__(self, *args, **kwargs):
        super(Pap, self).__init__(*args, **kwargs)
        self.disable_js()

    @property
    def list(self):
        elements = self.find_elements_by_css_selector(".search-list-item")
        res = [Annonce.from_element(i) for i in elements]
        return res


if __name__ == '__main__':
    conf = ConfigPap()
    conf.headless = False
    conf.start_anonymously = False
    conf.use_proxy = False

    pap = Pap(config=conf)
    with pap:
        pap.run()
