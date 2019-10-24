from argparse import ArgumentParser
from json import dump
from time import sleep
import numpy as np

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options

from leboncoin_kml.lbc import LBC, FinalPageReached


class CaptchaException(Exception):
    pass


def main(url, output_file, headless=False):
    options = Options()
    options.headless = headless
    driver = webdriver.Firefox(options=options)

    with open(output_file, "w") as fp:
        with LBC(driver, url) as d:
            try:
                while True:
                    sleep(np.random.normal(1, 0.1))
                    if d.blocked:
                        if headless:
                            raise CaptchaException("Felt into captcha")
                        while d.blocked:
                            print("Please solve captcha")
                            sleep(np.random.normal(2, 0.1))
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
    return parser.parse_args()


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    args = parse()

    main(url, **args.__dict__)
