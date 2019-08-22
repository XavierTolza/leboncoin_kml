import logging
from os.path import isfile, abspath, dirname, join

import numpy as np
import schedule as schedule
from dotdict import dotdict

from leboncoin_kml.common import get_template
from lxml import etree

wrapper = u'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2">%s</kml>'


class KMLEncoder(object):
    def __init__(self, filename, price_scale):
        self.price_scale = price_scale
        self.filename = filename
        self.log = logging.Logger("KML", level=logging.INFO)
        self.container = etree.Element("Document")

    def start(self):
        file = self.filename
        if isfile(file):
            raise ValueError("File %s already exists" % file)

    def flush(self):
        xml = self.container
        xml = etree.tostring(xml).decode("utf-8")
        xml = wrapper % xml
        with open(self.filename, "w") as fp:
            fp.write(xml)

    def stop(self):
        self.log.info("Stopping KML logger, flushing changes to file")
        self.flush()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def append(self, item):
        xml = Placemark(item).to_xml(self.price_scale)
        self.container.append(xml)

    def __call__(self, item):
        self.append(item)


class Placemark(object):
    template_file = "description.html"

    def __init__(self, item):
        self.item = dotdict(item)

    @property
    def html_description(self):
        res = get_template(self.template_file).render(item=self.item)
        wrapper = "<![CDATA[\n%s\n]]>"
        # wrapper = "%s"
        return wrapper % res

    def __str__(self):
        return etree.tostring(self.to_xml())

    def to_xml(self, price_scale):
        item = self.item
        res = etree.Element("Placemark")

        # Set name
        name = "%s %ik€" % (item.title[:20], item.price // 1000)
        etree.SubElement(res, "name").text = name

        # Set coordinates
        coordinates = np.array((item.lon, item.lat))
        coordinates += np.random.normal(0, 0.001, 2)
        coordinates = tuple(coordinates.tolist())
        coordinates_str = "%f,%f" % coordinates
        coordinates = etree.SubElement(etree.SubElement(res, "Point"), "coordinates")
        coordinates.text = coordinates_str

        # Set description
        etree.SubElement(res, "description").text = self.html_description

        # Set style
        price_scale = np.array(price_scale)
        prices = np.sort(np.ravel(price_scale))
        a = 1 / np.diff(prices)[0]
        b = -a * prices[0]
        price_scale = float(np.clip(a * item["price"] + b, 0, 1))
        green_red = bytes([int((1 - price_scale) * 255), int(price_scale * 255)]).hex()
        color_str = "ff00%s" % green_red
        etree.SubElement(etree.SubElement(etree.SubElement(res, "Style"), "IconStyle"), "color").text = color_str

        return res
