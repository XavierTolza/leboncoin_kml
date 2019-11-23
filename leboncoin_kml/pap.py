import re

import dateparser
import numpy as np
from fuzzywuzzy import fuzz
from pandas import DataFrame
from selenium.common.exceptions import NoSuchElementException

from leboncoin_kml.annonce import Annonce as LBCAnnonce
from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC
from leboncoin_kml.postal_code_db import db


class ConfigPap(Config):
    url = "https://www.pap.fr/annonce/vente-maisons-midi-pyrenees-g475-a-partir-du-3-pieces-jusqu-a-300000-euros-a-partir-de-60-m2"
    scrap_time = 49


class Annonce(LBCAnnonce):
    @classmethod
    def from_element(cls, driver, el):
        try:
            url = el.find_element_by_css_selector(".item-title").get_attribute("href")
            if "https://www.pap.fr" not in url:
                return None
            title = el.find_element_by_css_selector("span.h1").text
            price = int(el.find_element_by_css_selector("span.item-price").text.replace(".", "").split(" ")[0])
            driver.new_tab(url)
            images = [i.get_attribute("src") for i in driver.find_elements_by_css_selector("a.img-liquid img")]
            loc = driver.find_element_by_css_selector("div.item-description h2").text
            departement = int(re.match(".+\((\d{2,5})\).*", loc).groups()[0])
            villes = db.set_index("code").loc[departement]
            if type(villes) == DataFrame:
                ratio = [fuzz.ratio(loc.upper(), i.upper()) for i in villes.nom.values]
                ville = villes.iloc[np.argmax(ratio)]
            else:
                ville = villes
            id_date = driver.find_element_by_css_selector("p.item-date").text
            id, date = re.match("R.f[^a-zA-Z0-9]+([^ ]+) / (.+)", id_date).groups()
            date = dateparser.parse(date)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            body = driver.find_element_by_css_selector(".item-description").text
            url = driver.current_url
            driver.close_tab()
            id_hex = bytes(id, "utf-8").hex()
            res = dict(
                body=body,
                expiration_date=date,
                list_id=id_hex,
                first_publication_date=date,
                images=dict(nb_images=len(images), urls=images, urls_large=images, urls_thumb=images),
                index_date=date,
                price=[price],
                subject=title,
                url=url,
                location=dict(
                    city=ville.nom,
                    city_label=f"{ville.nom} {departement}",
                    lat=float(ville.gps.split(",")[0]),
                    lng=float(ville.gps.split(",")[1]),
                    zipcode=departement
                )
            )
            return Annonce(res)
        except NoSuchElementException as e:
            raise


class Pap(LBC):
    def __init__(self, *args, **kwargs):
        super(Pap, self).__init__(*args, **kwargs)
        self.disable_js()

    @property
    def list(self):
        elements = self.find_elements_by_css_selector(".search-list-item")
        res = (Annonce.from_element(self, i) for i in elements)
        res = [i for i in res if i is not None]
        return res

    @property
    def need_identity_change(self):
        title = self.title.lower()
        res = "accès refusé" in title and ("pap" not in title or title == "about:config")
        if res:
            self.log.debug("Need identity change because title is: %s" % title)
        return res

    @property
    def next_page_link(self):
        res = self.find_element_by_css_selector("ul li.next a").get_attribute("href")
        return res


if __name__ == '__main__':
    conf = ConfigPap()
    from logging import DEBUG

    conf.headless = False
    conf.start_anonymously = False
    conf.log_level = DEBUG
    conf.use_proxy = True
    conf.email_receivers = None

    pap = Pap(config=conf)
    with pap:
        pap.run()
