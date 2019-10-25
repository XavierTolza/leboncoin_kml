from argparse import ArgumentParser
from json import dump
from time import sleep, time

import numpy as np
from selenium.common.exceptions import NoSuchElementException

from leboncoin_kml.lbc import LBC, FinalPageReached
from leboncoin_kml.scrapper import Firefox


class CaptchaException(Exception):
    pass


def main(url, output_file, headless=False, sleep_time=10):

    t0 = -100 * sleep_time

    with open(output_file, "w") as fp:
        with LBC(Firefox(headless=headless), url) as d:
            try:
                while True:
                    if d.blocked:
                        if headless:
                            raise CaptchaException("Felt into captcha")
                        while d.blocked:
                            print("Please solve captcha")
                            sleep(np.random.normal(2, 0.1))

                    delta_t = time() - t0
                    sleep_duration = np.random.normal(sleep_time - delta_t, sleep_time / 10)
                    print(f"Last page took {delta_t} seconds. Sleeping {sleep_duration} to reach {sleep_time}")
                    if sleep_duration > 0:
                        sleep(sleep_duration)
                    t0 = time()

                    print("Getting page info")
                    all = d.list
                    try:
                        print("Parsing page")
                        annonces = [i.dict for i in all]
                        print("Going to next page")
                        d.got_to_next_page()
                    except NoSuchElementException as e:
                        print(str(e))

                    for i in annonces:
                        dump(i, fp)
                        fp.write("\n")
            except FinalPageReached:
                print("Finished research")


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-o", "--output_file", default="output.txt")
    parser.add_argument("-s", "--sleep_time", default=10, type=float)
    return parser.parse_args()


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    args = parse()

    main(url, **args.__dict__)
