from argparse import ArgumentParser
from json import dumps

from leboncoin_kml.lbc import LBC, FinalPageReached


def main(url, output_folder, headless=False, start_anonymously=False):
    d = LBC(url, output_folder, headless=headless, start_anonymously=start_anonymously)
    try:
        with d:
            d.run()
        print("finished")
    except FinalPageReached:
        print("Finished research")


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-o", "--output_folder", default="output")
    return parser.parse_args()


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    args = parse()

    main(url, **args.__dict__)
