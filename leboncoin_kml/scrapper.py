#!python3
# -*- coding: utf-8 -*-
# coding=utf-8
import difflib
import re
from argparse import ArgumentParser
from base64 import b64encode
from os.path import isfile, join

import numpy as np
import scrapy
from dotdict import dotdict
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.xlib.pydispatch import dispatcher

from leboncoin_kml.common import supprime_accent, id_from_url, http, encoding, headers
from leboncoin_kml.container import Container
from leboncoin_kml.postal_code_db import db
from leboncoin_kml.proxy import Mode


class Image(object):
    def __init__(self, url):
        self.url = url

    @property
    def filename(self):
        return self.url.split("/")[-1]

    @property
    def id(self):
        return self.filename.split(".")[0]

    def to_file(self, folder):
        img_bytes = self.bytes
        with open(join(folder, self.filename), "wb") as fp:
            fp.write(img_bytes)

    @property
    def bytes(self):
        data = http.request("GET", self.url, preload_content=False)
        img_bytes = data.read()
        return img_bytes


class LBCScrapper(scrapy.Spider):
    name = 'lbcscrapper'

    def __init__(self, url, filename, max_page=None):
        super(LBCScrapper, self).__init__()
        self.filename = filename
        self.max_page = max_page if max_page is not None else np.inf
        self.start_urls = [url]

        # Regex to find images
        self.image_regex = [
            re.compile("background-image:url\(.+"),
            re.compile("https://img\d.leboncoin.fr/ad-(image|thumb|large)/[0-9a-f]+.(jpg|png)")
        ]

        self.container = Container(filename)
        self.container.open()
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    @property
    def stopping(self):
        return getattr(self, "closed", None)

    def stop(self):
        setattr(self, "closed")

    def parse_page(self, response):
        page_url = response._url
        self.logger.info("Parsing page %s" % page_url)
        elements = response.xpath('//div[@itemprop="priceSpecification"]/../../..')
        for i, element in enumerate(elements):
            attribs = dotdict(element.attrib)
            if "title" in attribs and "href" in attribs and not self.stopping:
                url = attribs.href
                if id_from_url(url) not in self.container.ids:
                    self.logger.debug("Creating request for element %i of page %s" % (i, page_url))
                    request = response.follow(url, self.parse_element)
                    yield request
                else:
                    self.logger.info("Skipped %s" % url)

    def parse(self, response):
        current_url = response._url

        # Process first page
        r = re.compile(".+(&|/)p(age)?(-|=)(\d+)")
        try:
            current_page = int(r.findall(current_url)[0][-1])
        except IndexError:
            current_page = 1

        for i in self.parse_page(response):
            yield i

        # Find next page
        self.logger.debug("Searching for new pages on page %i" % current_page)
        if current_page < self.max_page and not self.stopping:
            bottom_links = [i.attrib["href"] for i in response.xpath("//nav/div/ul/li/a")]
            if len(bottom_links) == 0:
                raise ValueError("Failed to find links in the page")
            bottom_links = [i for i in bottom_links if len(i)]
            bottom_links = np.unique(bottom_links)
            page_numbers = [(r.findall(i), i) for i in bottom_links]
            page_numbers = [(i[0][-1], i[1]) for i in page_numbers if len(i[0])]
            links = [(int(i[-1]), link) for i, link in page_numbers if len(i)]
            page_numbers, links = zip(*links)
            page_numbers = np.array(page_numbers)
            links = np.array(links)

            selector = page_numbers > current_page
            if not np.any(selector):
                raise ValueError("No page is found links is greater than current page %i" % current_page)
            page_numbers, links = page_numbers[selector], links[selector]
            sorter = np.argsort(page_numbers)
            page_numbers = page_numbers[sorter]
            links = links[sorter]
            last_page_number = page_numbers[-1]

            for page_number, link in zip(page_numbers[:10], links):
                if page_number > self.max_page:
                    self.stop()
                    break
                if page_number == last_page_number:
                    method = self.parse
                else:
                    self.logger.info("Queued page %i: %s" % (page_number, link))
                    method = self.parse_page
                request = response.follow(link, method, priority=0)
                yield request
        self.logger.debug("Spider finished")

    def get_element_images(self, response):
        images = [i.attrib["style"] for i in response.xpath("//div[@style]")]
        images = [i.split("url(")[1].split(")")[0] for i in images if self.image_regex[0].match(i) is not None]
        images = [i.replace("-image", "-large") for i in images if self.image_regex[1].match(i) is not None]
        images = [Image(i) for i in images]
        return images

    @staticmethod
    def b64encode(data):
        return b64encode(bytes(data, encoding)).decode(encoding)

    def parse_element(self, response):
        # Extract info
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
            postal_code = int(postal_code)
            gps = db.loc[db.code == postal_code]
            city_maj = supprime_accent(city).upper()
            ratio = [difflib.SequenceMatcher(None, i, city_maj).ratio() for i in gps.nom.values]
            lat, lon = [float(i) for i in gps.assign(ratio=ratio).sort_values("ratio").iloc[0].gps.split(",")]
        except ValueError:
            city, postal_code = None, None
            lat, lon = None, None
        date, time = response.xpath('//div[@data-qa-id="adview_date"]/text()')[0].get().split(" à ")
        hour, minute = [int(i) for i in time.split("h")]
        day, month, year = [int(i) for i in date.split("/")]
        category = url.split(".fr/")[1].split("/")[0]

        # Append info
        result = dict(id=id, title=self.b64encode(title), url=url, images=[i.url for i in images],
                      description=self.b64encode(description), price=price, city=city,
                      postal_code=postal_code, category=category, day=day, month=month, year=year, hour=hour,
                      minute=minute, lat=lat, lon=lon)

        self.container.add_record(**result)
        for im in images:
            self.container.add_image(im.filename, im.bytes)

        self.logger.info("Parsed element in page %s" % response._url)

    def spider_closed(self, spider):
        self.container.close()


def scrap(url, out_file, max_page, use_proxy, proxylist, debug=False):
    n_concurrent_requests = 1000
    settings = dict(LOG_LEVEL="DEBUG" if debug else "INFO",
                    CONCURRENT_REQUESTS=n_concurrent_requests,
                    CONCURRENT_REQUESTS_PER_DOMAIN=n_concurrent_requests,
                    CONCURRENT_REQUESTS_PER_IP=n_concurrent_requests,
                    CONCURRENT_ITEMS=n_concurrent_requests,
                    LOG_STDOUT=True,
                    **headers)
    if use_proxy:
        middlewares = {
            # 'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
            'proxy.RandomProxy': 10,
            # 'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': None,
            'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': None,
            # 'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
        settings["DOWNLOADER_MIDDLEWARES"] = settings['SPIDER_MIDDLEWARES'] = middlewares

        settings.update(dict(PROXY_LIST=proxylist,
                             PROXY_MODE=Mode.RANDOMIZE_PROXY_ONCE,
                             DOWNLOAD_DELAY=1,
                             RETRY_ENABLED=False,
                             HTTPERROR_ALLOW_ALL=False,
                             DOWNLOAD_TIMEOUT=2,
                             RETRY_TIMES=20,
                             RETRY_HTTP_CODES=[500, 503, 504, 400, 403, 404, 408]))

    process = CrawlerProcess(settings)
    process.crawl(LBCScrapper, url, out_file, max_page)
    process.start()  # the script will block here until the crawling is finished


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("url", help="URL de départ sur le site leboncoin.")
    parser.add_argument("out_file", help="Fichier tar de sortie contenant les informations récupérées",
                        default="out.tar")
    parser.add_argument("-m", dest="max_page", help="Page max à atteindre", default=None, type=int)
    parser.add_argument("--use_proxy", "-p", action="store_true", help="Utilisation d'une liste de proxy")
    parser.add_argument("--proxylist", default="proxylist.txt", help="Specifier une liste de proxy manuelle")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug")

    args = parser.parse_args()
    scrap(**args.__dict__)
