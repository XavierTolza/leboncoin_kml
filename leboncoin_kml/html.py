import json
from datetime import timedelta, datetime
from os.path import abspath, join, dirname

from jinja2 import FileSystemLoader, Environment

from leboncoin_kml.annonce import Annonce

default_template_folder = join(dirname(abspath(__file__)), "assets")
import numpy as np


class HTMLFormatter(object):
    def __init__(self, template_folder=default_template_folder, template_name="report_template.html"):
        self.template_name = template_name
        templateLoader = FileSystemLoader(searchpath=template_folder)
        templateEnv = Environment(loader=templateLoader)
        self.env = templateEnv

    def get_template(self, fname):
        return self.env.get_template(fname)

    def format_duration(self, value):
        td = timedelta(seconds=value - 3600)
        date = datetime.fromtimestamp(0) + td
        res = f"{date.minute}m"
        if date.hour:
            res = f"{date.hour}h " + res
        return res

    def format_price(self, price):
        return '{:,}'.format(price).replace(',', ' ')

    def __call__(self, data):
        temp = self.get_template(self.template_name)
        elements = [Annonce(i) for i in list(data.values())]
        prices = []

        directions = {}

        for i in elements:
            i["images"] = list(zip(i.images_thumb, i.images_mini, i.images_large))
            price = i["price"][0]
            prices.append(price)
            i["price"] = self.format_price(price)
            i["price_int"] = price
            for dir_name, v in i["directions"].items():
                dir_name = dir_name.replace("_", " ").capitalize()
                if dir_name not in directions:
                    directions[dir_name] = []
                directions[dir_name].append(v[0]["legs"][0]["duration"]["value"])
            i["directions"] = {
                k.replace("_", " ").capitalize(): dict(text=self.format_duration(v[0]["legs"][0]["duration"]["value"]),
                                                       value=v[0]["legs"][0]["duration"]["value"])
                for k, v in i["directions"].items()}

        for k in directions.keys():
            directions[k] = dict(min=np.min(directions[k]), max=np.max(directions[k]))

        res = temp.render(title="Résultats de la recherche", elements=elements, json=json.dumps(elements),
                          price_min=np.min(prices), price_max=np.max(prices), directions=directions)
        return res


if __name__ == '__main__':
    with open("data.json", "r") as fp:
        data = json.load(fp)
    res = HTMLFormatter()(data)
    with open("/tmp/out.html", "w") as fp:
        fp.write(res)
    pass
