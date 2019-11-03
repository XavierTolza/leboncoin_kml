from googlemaps.client import Client as GClient
from googlemaps.exceptions import ApiError, TransportError, _RetriableRequest, Timeout
from openrouteservice import Client as OClient

from leboncoin_kml.config import Config
from leboncoin_kml.log import LoggingClass


class ORS(object):
    profiles = dict(bicycling="cycling-regular", driving="driving-car")

    def __init__(self, config=Config()):
        self.config = config
        self.client = OClient(key=config.openroute_api_key)

    def compile_duration(self, value):
        seconds = value % 60
        minutes = ((value - seconds) / 60) % 60
        hours = (value - seconds - minutes * 60)
        text = "%.0f min" % minutes
        if hours > 0:
            text = f"%.0f H " % hours + text
        return dict(text=text, value=value)

    def directions(self, start, destination, mode="driving", arrival_time=None):
        out = self.client.directions((start, destination), profile=self.profiles[mode])
        res = []
        for i in out["routes"]:
            s = i["summary"]
            res.append(dict(legs=[dict(distance=self.compile_distance(s["distance"]),
                                       duration=self.compile_duration(s["duration"]))]))
        return res

    def compile_distance(self, value):
        return dict(text="%.2f km" % (value / 1000), value=value)


class Client(LoggingClass):
    def __init__(self, config=Config()):
        super(Client, self).__init__(config)
        self.config = config
        self.gmap = GClient(config.google_maps_api_key)
        self.ors = ORS(config)

    def directions(self, *args, **kwargs):
        try:
            res = self.gmap.directions(*args, **kwargs)
        except (ApiError, TransportError, _RetriableRequest, Timeout) as e:
            name = type(e).__name__
            self.warning(f"Google maps failed, switched back to ORS directions.\n"
                         f"Error is {name}: {str(e)}")
            res = self.ors.directions(*args, **kwargs)
        return res
