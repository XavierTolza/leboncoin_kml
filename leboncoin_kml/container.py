from os import mkdir
from os.path import join, isdir, abspath

from memapdict import memapdict
import umsgpack


class Container(memapdict):
    def __init__(self, folder, parser_name):
        folder = abspath(folder)
        if not isdir(folder):
            mkdir(folder)
        super(Container, self).__init__(join(folder, parser_name.lower()))

    def __setattr__(self, key, value):
        return object.__setattr__(self, key, value)

    def __getattr__(self, item):
        return object.__getattribute__(self, item)

    def __setitem__(self, key, value):
        abspath = self._abspath_(key)
        self.write(abspath, umsgpack.dumps(value))

    def __getitem__(self, item):
        abspath = self._abspath_(item)
        with open(abspath, "rb") as fp:
            res = umsgpack.load(fp)
        return res
