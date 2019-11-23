import re
from time import sleep

import dateparser
import numpy as np
from fuzzywuzzy import fuzz
from pandas import DataFrame
from selenium.common.exceptions import NoSuchElementException

from leboncoin_kml.annonce import Annonce as LBCAnnonce
from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC
from leboncoin_kml.postal_code_db import db


class ConfigBienIci(Config):
    url = "https://www.bienici.com/recherche/achat/haute-garonne-31/3-pieces-et-plus?prix-max=300000&tri=publication-desc&camera=8_0.2685465_43.442918_0.9_0"


class Annonce(LBCAnnonce):
    @classmethod
    def from_element(cls, url, driver):
        try:
            body = driver.find_element_by_css_selector("div.descriptionContent").text
            title = driver.find_element_by_css_selector("h1").text
            price = int(driver.find_element_by_css_selector("span.thePrice").text.replace(".", "")
                        .replace(" ", "").replace("€", ""))

            loc = driver.find_element_by_css_selector("span.fullAddress").text

            ville, departement = re.match("([a-zA-Z]+) ?(\d{2,5}).*", loc).groups()
            departement = int(departement)
            villes = db.set_index("code").loc[departement]
            if type(villes) == DataFrame:
                ratio = [fuzz.ratio(ville.upper(), i.upper()) for i in villes.nom.values]
                ville = villes.iloc[np.argmax(ratio)]
            else:
                ville = villes

            images = driver.find_elements_by_css_selector("div.slideImg img")
            images = [i.get_attribute("src") for i in images]

            id_search = [i.text for i in driver.find_elements_by_css_selector("div.allDetails div.labelInfo")
                         if "réf" in i.text.lower()]
            id = id_search[0].split(":")[-1].replace(" ", "")

            date = driver.find_elements_by_css_selector("div.realEstateAdsMainInfo span")
            date = [i.text for i in date if "mis à jour" in i.text.lower()]
            if len(date):
                date = dateparser.parse(date[0])
                date = date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date = None
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


class BienIci(LBC):
    @property
    def list(self):
        elements = self.find_elements_by_css_selector("article.sideListItem")
        n_elements = len(elements)
        urls = [i.find_element_by_css_selector("a.detailedSheetLink").get_attribute("href") for i in elements]
        res = []
        urls = urls[:2]
        for url in urls:
            self.new_tab(url, wait_page_load=url == urls[-1])
        while self.n_tabs > 1:
            res.append(Annonce.from_element(self.current_url, self))
            self.close_tab()
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

    def wait_page_load(self):
        while self.find_element_by_css_selector("div.kimono-loadingView").value_of_css_property("display") != "none":
            sleep(1)


if __name__ == '__main__':
    conf = ConfigBienIci()
    from logging import DEBUG

    conf.headless = False
    conf.start_anonymously = False
    conf.log_level = DEBUG
    conf.use_proxy = True
    conf.email_receivers = None

    bi = BienIci(config=conf)
    with bi:
        bi.run()
