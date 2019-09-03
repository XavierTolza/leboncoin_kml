import json
import logging
import re
import tarfile
from argparse import ArgumentParser
from base64 import b64decode
from contextlib import closing
from io import BytesIO
from multiprocessing import Lock
from os.path import abspath, isfile, basename
from time import time

from leboncoin_kml.common import encoding
from leboncoin_kml.kml import KMLEncoder, ConvertError

log = logging.getLogger("container")
lock = Lock()



class Container(object):
    open_mode = "a"

    def __init__(self, filename):
        self.filename = abspath(filename)
        self.tar = None
        self.ids = {}

    def open(self):
        if not isfile(self.filename):
            # Create file
            self.tar = tarfile.open(self.filename, self.open_mode)
            self.mkdir("images", "annonces")
        else:
            try:
                self.tar = tarfile.open(self.filename, self.open_mode)
            except tarfile.ReadError as e:
                raise tarfile.ReadError("Impossible to open archive %s: %s" % (self.filename, str(e)))
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
        lock.acquire()
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        lock.release()

    def add_record(self, id, **kwargs):
        data = bytes(json.dumps(dict(id=id, **kwargs)), encoding)
        filename = "annonces/%i" % id
        self.addfile(filename, data)
        self.ids[id] = None

    def add_image(self, filename, data):
        self.addfile("images/%s" % filename, data)

    def addfile(self, filename, content_bytes):
        with self:
            with closing(BytesIO(content_bytes)) as fobj:
                tarinfo = tarfile.TarInfo(filename)
                tarinfo.size = len(fobj.getvalue())
                tarinfo.mtime = time()
                self.tar.addfile(tarinfo, fileobj=fobj)

    def get_record(self, id):
        tar = self.tar
        data = tar.extractfile("annonces/%i" % id).read()
        data = json.loads(data.decode(encoding))
        for field in "title,description".split(","):
            data[field] = b64decode(bytes(data[field], encoding)).decode(encoding)
        return data

    def export_kml(self, out_file, price_scale):
        with KMLEncoder(out_file, price_scale) as encoder:
            for id in self.ids.keys():
                record = self.get_record(id)
                try:
                    encoder.append(record)
                except ConvertError:
                    pass


class ReadOnlyContainer(Container):
    open_mode = "r"


def encode_kml(src, out):
    with ReadOnlyContainer(src) as c:
        c.export_kml(out, (0, 1000))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("out")
    args = parser.parse_args()

    encode_kml(**args.__dict__)
