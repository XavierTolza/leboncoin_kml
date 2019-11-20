import json
from datetime import timedelta, datetime
from os.path import abspath, join, dirname

from jinja2 import FileSystemLoader, Environment
from tqdm import tqdm

from leboncoin_kml.annonce import Annonce
from leboncoin_kml.config import Config

default_template_folder = join(dirname(abspath(__file__)), "assets")
import numpy as np


def extract_surface(name, **kwargs):
    def wrapper(i):
        val = getattr(i, name)
        if len(kwargs):
            val = val(**kwargs)
        if val is None:
            return None
        return val["valeur"]

    return wrapper


extract_garage = extract_surface("surface", elements=["garage"])


def apply_filters(i, filters):
    for filter in filters:
        if not filter(i):
            return False
    return True


class HTMLFormatter(object):
    def __init__(self, template_folder=default_template_folder, template_name="report_template.html", config=Config()):
        self.config = config
        self.filters = config.filters
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

    def __call__(self, data, use_tqdm=False):
        temp = self.get_template(self.template_name)
        elements = (Annonce(i) for i in list(tqdm(data.values(), disable=not use_tqdm)))
        elements = [i for i in elements if apply_filters(i, self.filters)]
        # Sort by price
        elements = np.array(elements)[np.argsort([i["price"][0] for i in elements])].tolist()
        prices = []

        directions = {}

        sliders = [
            dict(name="Jardin", step=10, unit="m²", id="surf_jardin", func=extract_surface("surface_jardin")),
            dict(name="Terrain", step=10, unit="m²", id="surf_terrain",
                 func=extract_surface("surface_terrain")),
            dict(name="Latitude", step=0.001, unit="°", id="lat", func=lambda x: x.latlng[0], precision=4,
                 display=False),
            dict(name="Longitude", step=0.001, unit="°", id="lng", func=lambda x: x.latlng[1], precision=4,
                 display=False)
        ]
        for i in sliders:
            i["min"] = np.inf
            i["max"] = -np.inf
            if "precision" not in i:
                i["precision"] = 0
            if "display" not in i:
                i["display"] = True

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

            i["sliders"] = {}
            for slider in sliders:
                val = slider["func"](i)
                i["sliders"][slider["id"]] = val
                if val is not None:
                    slider["min"] = min(slider["min"], val)
                    slider["max"] = max(slider["max"], val)

            i["metrics"] = {"Garage": dict(value=extract_garage(i), unit="m²")}
            i["coordinates"] = i.latlng.tolist()

        latlng = np.array([i.latlng for i in elements])
        map_zoom = int(np.round(np.std(latlng, axis=0).max()*117.57))

        for k in directions.keys():
            directions[k] = dict(min=np.min(directions[k]), max=np.max(directions[k]))

        res = temp.render(title="Résultats de la recherche", elements=elements, json=json.dumps(elements),
                          price_min=np.min(prices), price_max=np.max(prices), directions=directions, sliders=sliders,
                          mapbox_token=self.config.mapbox_token, map_center=latlng.mean(0).tolist(), map_zoom=map_zoom)
        return res


if __name__ == '__main__':
    with open("data.json", "r") as fp:
        data = json.load(fp)
    filters = Config().filters
    res = HTMLFormatter()(data)
    with open("/tmp/out.html", "w") as fp:
        fp.write(res)
    pass
