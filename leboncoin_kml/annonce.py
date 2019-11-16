import datetime


class Annonce(dict):
    pass


class AnnonceLBC(Annonce):

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
        return


class AnnoncesHolder(list):
    def __init__(self, data, main_class=AnnonceLBC):
        super(AnnoncesHolder, self).__init__(data)
        self.main_class = main_class

    def __getitem__(self, item):
        return self.main_class(super(AnnoncesHolder, self).__getitem__(item))
