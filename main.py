import traceback
from os import remove
from os.path import isfile

from leboncoin_kml.config import Config
from leboncoin_kml.lbc import LBC, read_file
from leboncoin_kml.mail import Sender


def main():
    conf = Config()

    log_file = conf.log_file
    if log_file is not None and isfile(log_file):
        remove(log_file)
    n_error = 0

    finished = False
    previous_result = {}
    while not finished:
        d = LBC(conf, previous_result=previous_result)
        try:
            with d:
                d.run()
            finished = True
        except Exception as e:
            d.log.error("Restarting scrapper")
            n_error += 1
            tb = traceback.format_exc()
            d.log.critical(f"General error (counter={n_error}): \n{str(type(e))}: {str(e)}\n{tb}")

            if n_error > 10:
                d.log.critical("Too many critical errors, stopping the bot")
                finished = True
                # Too many failures, sending the mail
                sender = Sender(conf)

                attachments = {"log.txt": read_file(conf.log_file)}
                # noinspection PyBroadException
                try:
                    attachments.update(d.make_attachments(d.result))
                except Exception:
                    pass

                if hasattr(e, "info"):
                    attachments.update(e.info)
                sender(attachments, "Erreur robot LBC", "Ci joint des infos sur le plantage du robot")
            else:
                conf.url = d.current_lbc_url
                previous_result = d.result

    print("finished execution")


if __name__ == '__main__':
    main()
