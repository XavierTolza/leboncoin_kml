from argparse import ArgumentParser

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC, FinalPageReached


def main(headless=False):
    conf = Config()
    conf.headless = headless

    d = LBC(conf)
    try:
        with d:
            d.run()
        print("finished")
    except FinalPageReached:
        print("Finished research")

    items = d.container.new_items


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse()

    main(**args.__dict__)
