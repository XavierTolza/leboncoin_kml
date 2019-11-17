import re
from datetime import datetime

import numpy as np


class Annonce(dict):
    @property
    def datetime(self):
        return datetime.strptime(self["index_date"], '%Y-%m-%d %H:%M:%S')

    @property
    def coordinates(self):
        return (self["location"]["lat"], self["location"]["lng"])

    @property
    def id(self):
        return self["list_id"]

    @property
    def city(self):
        loc = self["location"]
        if "city" in loc:
            return loc["city"]
        from leboncoin_kml.postal_code_db import db
        cities = db["lat,lng".split(",")].values
        ref = self.latlng
        city_index = np.nanargmin(np.linalg.norm(cities - ref[None], axis=1))
        res = db.iloc[city_index].nom.capitalize()
        return res

    @property
    def latlng(self):
        loc = self["location"]
        return np.array([loc["lat"], loc["lng"]]).astype(np.float)

    def __get_images(self, order):
        if 'images' in self:
            images = self["images"]
            for i in order:
                if i in images:
                    return images[i]
        return []

    @property
    def images_thumb(self):
        return self.__get_images("urls_thumb,urls,urls_large".split(','))

    @property
    def images_mini(self):
        return self.__get_images("urls,urls_large,urls_thumb".split(','))

    @property
    def images_large(self):
        return self.__get_images("urls_large,urls,urls_thumb".split(','))

    def __get_surface(self, elements):
        body = self["body"].replace("\n", "").replace("\r", "").lower()
        r = f'.*({"|".join(elements)})([a-z éè]{3, 20})?( de| d\'environ| ?: ?)? ?([0-9]+) ?m(²|2).*'
        match = re.match(r, body)
        res = None
        if match is not None:
            groups = match.groups()
            res = {k: t(groups[i]) for k, i, t in zip("type,valeur".split(","), [0, -2], (str, float))}
        return res

    @property
    def surface_terrain(self):
        return self.__get_surface("terrain,parcelle".split(","))

    @property
    def surface_jardin(self):
        return self.__get_surface("jardin,jardinet,potager".split(","))

    @property
    def a_construire(self):
        body = self["body"].replace("\n", "").replace("\r", "").lower()
        r = ".*(a|à|projet)( de)? (construire|construction).*"
        match = re.match(r, body)
        res = match is not None
        return res


class Location(dict):
    pass


class AnnoncesHolder(list):
    def __init__(self, data, main_class=Annonce):
        super(AnnoncesHolder, self).__init__(data)
        self.main_class = main_class

    def __getitem__(self, item):
        return self.main_class(super(AnnoncesHolder, self).__getitem__(item))
