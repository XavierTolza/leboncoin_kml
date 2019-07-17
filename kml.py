import logging
from os.path import isfile

import numpy as np
import schedule as schedule
from dotdict import dotdict

from templates import get_template
from lxml import etree

wrapper = u'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2">%s</kml>'


class KMLEncoder(object):
    def __init__(self, filename, flush_interval=30):
        self.filename = filename
        self.log = logging.Logger("KML", level=logging.INFO)
        self.container = etree.Element("Document")
        schedule.every(flush_interval).seconds.do(self.flush)

    def start(self):
        file = self.filename
        if isfile(file):
            self.fp = fp = open(file, "r+")
            content = fp.read()
            xml = etree.XML(bytes(content, "utf-8"))
            try:
                self.container = xml[0]
            except IndexError:
                pass
        else:
            self.flush()

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
        xml = Placemark(item).to_xml()
        self.container.append(xml)
        schedule.run_pending()

    def __call__(self, item):
        self.append(item)

    @property
    def n_items(self):
        return len(self.container)

    @property
    def already_done(self):
        descriptions = (i[2].text for i in self.container)
        res = [i.split("a href=\"")[1].split("\"")[0] for i in descriptions]
        return res


class Placemark(object):
    def __init__(self, item):
        self.item = dotdict(item)

    @property
    def html_description(self):
        res = get_template("description.html").render(item=self.item)
        wrapper = "<![CDATA[\n%s\n]]>"
        # wrapper = "%s"
        return wrapper % res

    def __str__(self):
        return etree.tostring(self.to_xml())

    def to_xml(self):
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
        green_red = bytes([int((1 - item.price_scale) * 255), int((item.price_scale) * 255)]).hex()
        color_str = "ff00%s" % green_red
        etree.SubElement(etree.SubElement(etree.SubElement(res, "Style"), "IconStyle"), "color").text = color_str

        return res
