from datetime import datetime, timedelta
from logging import DEBUG, INFO
from .common import DEBUG as is_debugging
from os.path import abspath, basename, join

from attr import dataclass
from numpy import inf

from .secret import *

tomorrow = datetime.today() + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y-%m-%d")
tomorrow_morning = datetime.strptime(tomorrow_str + " 9:00:00", '%Y-%m-%d %H:%M:%S').timestamp()


@dataclass
class Config(object):
    log_level = DEBUG
    log_file = "log.txt"
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=Pau_64000__43.2965_-0.37432_7305_30000&" \
          "real_estate_type=1&price=75000-200000&rooms=3-max&square=70-max"
    scrap_time = 25  # hours
    maximum_number_retry = 20
    loading_timeout = 5  # sec
    headless = not is_debugging
    output_folder = join(basename(abspath(__file__)), "../../bdd_lbc_gui")
    start_anonymously = True
    use_proxy = start_anonymously
    solve_captcha_by_hand = not use_proxy
    google_maps_api_key = google_maps_api_key
    openroute_api_key = openroute_api_key
    directions = dict(
        # boulot_velo=(inf, dict(
        #     destination=work,
        #     mode="bicycling",
        #     arrival_time=tomorrow_morning
        # )),
        boulot_voiture=(inf, dict(
            destination=work,
            mode="driving",
            arrival_time=tomorrow_morning
        )),
        Pau=(inf, dict(
            destination="Pau 31400",
            mode="driving",
            arrival_time=tomorrow_morning
        )),
    )
    filters = [
        lambda x: (not x.a_construire)
    ]
    email_receivers = email_dest
    email_sender = email_sender
    email_password = email_password
    encoding = "utf-8"
    skip_elements_already_in_bdd = False
    mapbox_token = mapbox_token
