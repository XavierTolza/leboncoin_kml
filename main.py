import difflib
import logging
import re
from argparse import ArgumentParser

import numpy as np
import scrapy
from dotdict import dotdict
from scrapy.crawler import CrawlerProcess

from kml import KMLEncoder
from postal_code_db import db
from requests import http, headers
from tools import supprime_accent, id_from_url

logging.getLogger("scrapy").setLevel(logging.WARNING)
logging.getLogger("scrapy.core.engine").setLevel(logging.WARNING)


class Scrapper(scrapy.Spider):
    name = 'lbcscrapper'

    def __init__(self, url, callback, prices_scale=None, max_page=None, already_done=[]):
        super(Scrapper, self).__init__()
        self.already_done = {id_from_url(url):url for url in already_done}
        self.max_page = max_page if max_page is not None else np.inf
        if prices_scale is not None:
            prices = np.sort(np.ravel(prices_scale))
            self.a = a = 1 / np.diff(prices)[0]
            self.b = -a * prices[0]
        else:
            self.a, self.b = 0, 0
        self.callback = callback
        self.start_urls = [url]
        self.image_regex = [
            re.compile("background-image:url\(.+"),
            re.compile("https://img\d.leboncoin.fr/ad-(image|thumb|large)/[0-9a-f]+.(jpg|png)")
        ]
        self.n_items = 0

    @staticmethod
    def download_file(url):
        return http.request("GET", url, preload_content=False)

    def parse_page(self, response):
        self.logger.info("Parsing page %s" % response._url)
        elements = response.xpath('//div[@itemprop="priceSpecification"]/../../..')
        for element in elements:
            attribs = dotdict(element.attrib)
            if "title" in attribs and "href" in attribs:
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
        if current_page < self.max_page:
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
        price_scale = float(np.clip(self.a * price + self.b, 0, 1))

        result = dict(id=id, title=title, url=url, images=images,
                      description=description, price=price, city=city, postal_code=postal_code, category=category,
                      day=day, month=month, year=year, hour=hour, minute=minute, lat=lat, lon=lon,
                      price_scale=price_scale)
        self.n_items += 1
        self.logger.info("Parsed element in page %s" % response._url)
        self.callback(result)


def main(url, out_file, echelle, max_page, use_proxy):
    settings = dict(LOG_LEVEL="INFO", CONCURRENT_REQUESTS=1000, CONCURRENT_REQUESTS_PER_DOMAIN=1000,
                    CONCURRENT_REQUESTS_PER_IP=1000, CONCURRENT_ITEMS=1000, **headers)
    if use_proxy:
        settings["DOWNLOADER_MIDDLEWARES"] = {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'proxy.RandomProxy': 100,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
        settings.update(dict(PROXY_LIST='proxylist.txt', PROXY_MODE=0, RETRY_ENABLED=True,
                             RETRY_TIMES=10, RETRY_HTTP_CODES=[500, 503, 504, 400, 403, 404, 408]))

    process = CrawlerProcess(settings)

    with KMLEncoder(out_file) as encoder:
        process.crawl(Scrapper, url, encoder, echelle, max_page, encoder.already_done)
        process.start()  # the script will block here until the crawling is finished
        print(encoder.n_items)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("url", help="URL de départ sur le site leboncoin.")
    parser.add_argument("out_file", help="Fichier KML de sortie", default="out.kml")
    parser.add_argument("--echelle_prix", "-e", dest="echelle",
                        help="Echelle de prix pour afficher le prix comme une couleur de point dans le KML",
                        default=None, type=lambda x: [int(i) for i in x.split(",")])
    parser.add_argument("-m", dest="max_page", help="Page max", default=None, type=int)
    parser.add_argument("--use_proxy", "-p", action="store_true", help="Use tor proxy")

    args = parser.parse_args()
    main(**args.__dict__)
