import json
import re
import tarfile
from contextlib import closing
from io import BytesIO
from os.path import abspath, isfile, basename
from time import time

from leboncoin_kml.common import encoding


class Container(object):
    def __init__(self, filename):
        self.filename = abspath(filename)
        self.tar = None
        self.ids = {}

    def open(self):
        if not isfile(self.filename):
            # Create file
            self.tar = tarfile.open(self.filename, "w")
            self.mkdir("images", "annonces")
        else:
            self.tar = tarfile.open(self.filename, "a")
            self.ids = {int(i): None for i in self.listdir("annonces")}
        pass

    def mkdir(self, *paths):
        for path in paths:
            t = tarfile.TarInfo(path)
            t.type = tarfile.DIRTYPE
            self.tar.addfile(t)

    def listdir(self, path):
        r = re.compile("%s.+" % path)
        res = [basename(i) for i in self.tar.getnames() if r.fullmatch(i) is not None]
        return res

    def close(self):
        self.tar.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def add_record(self, id, **kwargs):
        data = bytes(json.dumps(dict(id=id, **kwargs)), encoding)
        filename = "annonces/%i" % id
        self.addfile(filename, data)
        self.ids[id] = None

    def add_image(self, filename, data):
        self.addfile("images/%s" % filename, data)

    def addfile(self, filename, content_bytes):
        with closing(BytesIO(content_bytes)) as fobj:
            tarinfo = tarfile.TarInfo(filename)
            tarinfo.size = len(fobj.getvalue())
            tarinfo.mtime = time()
            self.tar.addfile(tarinfo, fileobj=fobj)
