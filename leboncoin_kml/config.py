from datetime import datetime, timedelta
from logging import INFO

from attr import dataclass
from numpy import inf

from .secret import *

tomorrow = datetime.today() + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y-%m-%d")


@dataclass
class Config(object):
    log_level = INFO
    log_file = "log.txt"
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&" \
          "real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    scrap_time = 25  # hours
    maximum_number_retry = 20
    loading_timeout = 5  # sec
    headless = True
    output_folder = "/tmp/output"
    start_anonymously = headless
    use_proxy = start_anonymously
    google_maps_api_key = google_maps_api_key
    openroute_api_key = openroute_api_key
    directions = dict(
        boulot_velo=(inf, dict(
            destination=work,
            mode="bicycling",
            arrival_time=datetime.strptime(tomorrow_str + " 9:00:00", '%Y-%m-%d %H:%M:%S').timestamp()
        )),
        boulot_voiture=(30, dict(
            destination=work,
            mode="driving",
            arrival_time=datetime.strptime(tomorrow_str + " 9:00:00", '%Y-%m-%d %H:%M:%S').timestamp()
        ))

    )
    filters = [
        lambda x: (x.latlng[0] < 43.597221 and x.latlng[0] > 43.444315
                   and x.latlng[1] > 1.350069
                   and not x.a_construire)
    ]
    email_receivers = email_dest
    email_sender = email_sender
    email_password = email_password
    encoding = "utf-8"
    skip_elements_already_in_bdd = False
