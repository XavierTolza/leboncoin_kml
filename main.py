from os import remove
from os.path import isfile

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC


def main():
    conf = Config()

    log_file = conf.log_file
    if log_file is not None and isfile(log_file):
        remove(log_file)

    d = LBC(conf)
    with d:
        d.run()
    print("finished execution")


if __name__ == '__main__':
    main()
