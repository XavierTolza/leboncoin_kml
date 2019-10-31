from os import remove
from os.path import isfile
from traceback import print_tb

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
        d = LBC(conf, previous_result=previous_result)
        try:
            with d:
                d.run()
            finished = True
        except MaximumNumberOfFailures as e:
            print("Restarting scrapper")
            conf.url = e.last_url
            previous_result = e.result
        except Exception as e:
            print(f"General error: {str(e)}")
            print_tb()
            conf.url = d.current_lbc_url
            previous_result = d.result

    print("finished execution")


if __name__ == '__main__':
    main()
