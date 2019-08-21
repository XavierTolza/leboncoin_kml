import difflib
import re

import numpy as np
import scrapy
from dotdict import dotdict

from leboncoin_kml.postal_code_db import db
from requests import http
from tools import supprime_accent, id_from_url


class LBCScrapper(scrapy.Spider):
    name = 'lbcscrapper'

    def __init__(self, url, csvfile, max_page=None):
        super(LBCScrapper, self).__init__()
        self.csvfile = csvfile
        self.max_page = max_page if max_page is not None else np.inf
        self.start_urls = [url]

        # Regex to find images
        self.image_regex = [
            re.compile("background-image:url\(.+"),
            re.compile("https://img\d.leboncoin.fr/ad-(image|thumb|large)/[0-9a-f]+.(jpg|png)")
        ]

    @staticmethod
    def download_file(url):
        return http.request("GET", url, preload_content=False)

    @property
    def stopping(self):
        return getattr(self, "closed", None)

    def parse_page(self, response):
        self.logger.info("Parsing page %s" % response._url)
        elements = response.xpath('//div[@itemprop="priceSpecification"]/../../..')
        for i, element in enumerate(elements):
            self.logger.debug("Creating request for element %i of page %s" % (i, response._url))
            attribs = dotdict(element.attrib)
            if "title" in attribs and "href" in attribs and not self.stopping:
                url = attribs.href
                if id_from_url(url) not in self.already_done:
                    request = response.follow(url, self.parse_element)
                    yield request
                else:
                    self.logger.info("Skipped %s" % url)

    def parse(self, response):
        for i in self.parse_page(response):
            yield i

        # Find next page
        r = re.compile("&page=(\d+)")
        try:
            current_page = int(r.findall(response._url)[0])
        except IndexError:
            current_page = 1
        if current_page < self.max_page and not self.stopping:
            bottom_links = [i.attrib["href"] for i in response.xpath("//nav/div/ul/li/a")]
            page_number, bottom_link_index = zip(*[(int(i[0]), index)
                                                   for index, i in enumerate(r.findall(i) for i in bottom_links) if
                                                   len(i)])
            page_number = np.array(page_number)
            page_number[page_number <= current_page] = np.max(page_number) + 10
            next_page_url = bottom_links[bottom_link_index[np.argsort(page_number)[0]]]
            yield response.follow(next_page_url, self.parse, dont_filter=True)

    def get_element_images(self, response):
        images = [i.attrib["style"] for i in response.xpath("//div[@style]")]
        images = [i.split("url(")[1].split(")")[0] for i in images if self.image_regex[0].match(i) is not None]
        images = [i.replace("-image", "-large") for i in images if self.image_regex[1].match(i) is not None]
        images_id = [i.split("/")[1] for i in images]
        images_bin = [self.download_file(im).data for im in images]
        images = [dict(url=url, id=id, bin=bin) for url, id, bin in zip(images, images_id, images_bin)]
        return images

    def parse_element(self, response):
        images = self.get_element_images(response)
        description = response.xpath('//div[text()="Description"]/following::div/div/div/span/text()')[0].get()
        title = response.xpath("//h1/text()")[0].get()
        url = response._url
        id = id_from_url(url)
        prices = response.xpath('//div[@data-qa-id="adview_price"]/div/span')
        price = np.unique([int(i.css("::text").get().replace(" ", "")) for i in prices]).tolist()[0]
        loc = response.xpath('//div[@data-qa-id="adview_location_informations"]/span/text()')
        try:
            city, _, postal_code = [i.get() for i in loc]
        except ValueError:
            city, postal_code = None, None
        postal_code = int(postal_code)
        gps = db.loc[db.code == postal_code]
        city_maj = supprime_accent(city).upper()
        ratio = [difflib.SequenceMatcher(None, i, city_maj).ratio() for i in gps.nom.values]
        lat, lon = [float(i) for i in gps.assign(ratio=ratio).sort_values("ratio").iloc[0].gps.split(",")]
        date, time = response.xpath('//div[@data-qa-id="adview_date"]/text()')[0].get().split(" à ")
        hour, minute = [int(i) for i in time.split("h")]
        day, month, year = [int(i) for i in date.split("/")]
        category = url.split(".fr/")[1].split("/")[0]

        result = dict(id=id, title=title, url=url, images=images,
                      description=description, price=price, city=city, postal_code=postal_code, category=category,
                      day=day, month=month, year=year, hour=hour, minute=minute, lat=lat, lon=lon)
        self.logger.info("Parsed element in page %s" % response._url)