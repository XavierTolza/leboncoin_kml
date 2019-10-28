from argparse import ArgumentParser
from json import dumps

from leboncoin_kml.lbc import LBC, FinalPageReached


def main(url, output_file, headless=False, start_anonymously=True):
    with open(output_file, "w") as fp:
        d = LBC(url, headless=headless, start_anonymously=start_anonymously)
        try:
            with d:
                d.run(lambda x: [fp.write(dumps(i).replace("\n", "") + "\n") for i in x])
            print("finished")
        except FinalPageReached:
            print("Finished research")


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-o", "--output_file", default="output.txt")
    return parser.parse_args()


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    args = parse()

    main(url, **args.__dict__)
