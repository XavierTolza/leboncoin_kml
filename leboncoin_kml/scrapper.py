import difflib
import re
from base64 import b64encode
from os.path import isfile, join, isdir

import numpy as np
import scrapy
from dotdict import dotdict
from pandas import read_csv, DataFrame, Series
from scrapy import signals

from leboncoin_kml.postal_code_db import db
from scrapy.xlib.pydispatch import dispatcher
from .common import supprime_accent, id_from_url, http, encoding


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
        data = http.request("GET", self.url, preload_content=False)
        with open(join(folder, self.filename), "wb") as fp:
            fp.write(data.read())


class LBCScrapper(scrapy.Spider):
    name = 'lbcscrapper'

    def __init__(self, url, csvfile, images_folder=None, max_page=None):
        super(LBCScrapper, self).__init__()
        self.images_folder = images_folder
        self.csvfile = csvfile
        self.max_page = max_page if max_page is not None else np.inf
        self.start_urls = [url]

        # Regex to find images
        self.image_regex = [
            re.compile("background-image:url\(.+"),
            re.compile("https://img\d.leboncoin.fr/ad-(image|thumb|large)/[0-9a-f]+.(jpg|png)")
        ]

        self.container = DataFrame()
        self.load_container()
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    @property
    def stopping(self):
        return getattr(self, "closed", None)

    def load_container(self):
        if isfile(self.csvfile):
            self.container = read_csv(self.csvfile).set_index("Index")

    def save_container(self):
        self.container.index.name = "Index"
        self.container.to_csv(self.csvfile)

    def parse_page(self, response):
        self.logger.info("Parsing page %s" % response._url)
        elements = response.xpath('//div[@itemprop="priceSpecification"]/../../..')
        for i, element in enumerate(elements):
            self.logger.debug("Creating request for element %i of page %s" % (i, response._url))
            attribs = dotdict(element.attrib)
            if "title" in attribs and "href" in attribs and not self.stopping:
                url = attribs.href
                if len(self.container) == 0 or id_from_url(url) not in self.container["id"].values:
                    request = response.follow(url, self.parse_element)
                    yield request
                else:
                    self.logger.info("Skipped %s" % url)

    def parse(self, response):
        for i in self.parse_page(response):
            yield i

        # Find next page
        r = re.compile(".+/p-(\d+)")
        try:
            current_page = int(r.findall(response._url)[0])
        except IndexError:
            current_page = 1
        if current_page < self.max_page and not self.stopping:
            bottom_links = [i.attrib["href"] for i in response.xpath("//nav/div/ul/li/a")]
            bottom_links = [i for i in bottom_links if len(i)]
            page_number = [(r.findall(i), i) for i in bottom_links]
            links = [(int(i[0]), link) for i, link in page_number if len(i)]
            page_number, links = zip(*links)
            page_number = np.array(page_number)
            page_number[page_number <= current_page] = np.max(page_number) + 10
            next_page_url = links[np.argmin(page_number)]
            yield response.follow(next_page_url, self.parse, dont_filter=True)

    def get_element_images(self, response):
        images = [i.attrib["style"] for i in response.xpath("//div[@style]")]
        images = [i.split("url(")[1].split(")")[0] for i in images if self.image_regex[0].match(i) is not None]
        images = [i.replace("-image", "-large") for i in images if self.image_regex[1].match(i) is not None]
        images = [Image(i) for i in images]
        return images

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

        # Save images if needed
        if isdir(self.images_folder):
            for im in images:  # type: Image
                im.to_file(self.images_folder)

        # Append info
        result = dict(id=id, title=title, url=url, images=b64encode(bytes(",".join([i.url for i in images]), encoding)),
                      description=b64encode(bytes(description, encoding)), price=price, city=city,
                      postal_code=postal_code, category=category, day=day, month=month, year=year, hour=hour,
                      minute=minute, lat=lat, lon=lon)
        self.container = self.container.append(Series(result), ignore_index=True)
        self.logger.info("Parsed element in page %s" % response._url)

    def spider_closed(self, spider):
        self.save_container()
