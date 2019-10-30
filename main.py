from argparse import ArgumentParser
from os import remove
from os.path import isfile

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC, FinalPageReached


def main(headless=False):
    conf = Config()
    conf.headless = headless

    log_file = conf.log_file
    if log_file is not None and isfile(log_file):
        remove(log_file)

    d = LBC(conf)
    try:
        with d:
            d.run()
        print("finished")
    except FinalPageReached:
        print("Finished research")


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse()

    main(**args.__dict__)
