from os import remove
from os.path import isfile

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC, MaximumNumberOfFailures


def main():
    conf = Config()

    log_file = conf.log_file
    if log_file is not None and isfile(log_file):
        remove(log_file)

    finished = False
    previous_result = {}
    while not finished:
        try:
            d = LBC(conf, previous_result=previous_result)
            with d:
                d.run()
            finished = True
        except MaximumNumberOfFailures as e:
            print("Restarting scrapper")
            conf.url = e.last_url
            previous_result = e.result
    print("finished execution")


if __name__ == '__main__':
    main()
