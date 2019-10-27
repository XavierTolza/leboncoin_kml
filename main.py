from argparse import ArgumentParser
from json import dumps

from selenium.common.exceptions import InsecureCertificateException

from leboncoin_kml.common import timeout_settings
from leboncoin_kml.lbc import LBC, FinalPageReached, ParserBlocked, WrongUserAgent
from leboncoin_kml.scrapper import ConnexionError, FindProxyError


class CaptchaException(Exception):
    pass


def main(url, output_file, headless=False):
    preferences = {i: 20 for i in timeout_settings}

    with open(output_file, "w") as fp:
        d = LBC(url, headless=headless, start_anonymously=True)
        d.set_preference(**preferences)
        need_refresh = False
        n_retry = 0
        try:
            with d:
                while True:
                    try:
                        if need_refresh:
                            d.refresh()
                            need_refresh = False

                        if d.blocked:
                            raise ParserBlocked("Reached captcha")
                        if "navigateur à jour" in d.title:
                            raise ParserBlocked("Need user agent change")
                        print("Getting page info")
                        annonces = d.list
                        n_retry = 0

                        for i in annonces:
                            fp.write(dumps(i).replace("\n", "") + "\n")

                        print(f"Parsed {len(annonces)} elements")
                        d.got_to_next_page()
                    except (ParserBlocked, WrongUserAgent, InsecureCertificateException,
                            ConnexionError, FindProxyError) as e:
                        n_retry += 1
                        print(f"Got error {str(type(e))}:{str(e)}. Changing identity ({n_retry} consecutive times)")
                        d.change_identity(proxy=type(e) != WrongUserAgent)
                        need_refresh = True
        except FinalPageReached:
            print("Finished research")
        finally:
            print("Closing browser")


def parse():
    parser = ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("-o", "--output_file", default="output.txt")
    return parser.parse_args()


if __name__ == '__main__':
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    args = parse()

    main(url, **args.__dict__)
