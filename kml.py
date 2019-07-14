import logging

import numpy as np
from dicttoxml import dicttoxml as toxml
import dicttoxml
from dotdict import dotdict

from templates import get_template


dicttoxml.LOG.setLevel(logging.ERROR)

class KMLEncoder(object):
    start_data = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
"""
    end_data = """</Document>
</kml>"""

    def __init__(self, filename):
        self.filename = filename
        self.fp = None
        self.n_items = 0

    def start(self):
        file = self.filename
        self.fp = fp = open(file, "w")
        fp.write(self.start_data)

    def stop(self):
        self.fp.write(self.end_data)
        self.fp.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def append(self, item):
        fp = self.fp
        fp.write(Placemark(item).__str__())
        fp.write("\n")
        self.n_items += 1
        # print(item)

    def __call__(self, item):
        self.append(item)


class Placemark(object):
    def __init__(self, item):
        self.item = item = dotdict(item)

    @property
    def html_description(self):
        res = get_template("description.html").render(item=self.item)
        wrapper = "<![CDATA[\n%s\n]]>"
        # wrapper = "%s"
        return wrapper % res

    def __str__(self):
        item = self.item
        coordinates = np.array((item.lon, item.lat))
        coordinates += np.random.normal(0, 0.001, 2)
        coordinates = tuple(coordinates.tolist())
        green_red = bytes([int((1 - item.price_scale) * 255),int((item.price_scale) * 255)]).hex()
        dic = dict(name="%s %ik€" % (item.title[:20], item.price // 1000), description=self.html_description,
                   Point=dict(coordinates="%f,%f" % coordinates),
                   Style=dict(IconStyle=dict(color="ff00%s" % green_red)))
        dic = dict(Placemark=dic)
        res = toxml(dic, root=False, attr_type=False).decode("utf-8")
        return res
