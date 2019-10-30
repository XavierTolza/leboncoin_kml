from datetime import datetime, timedelta
from logging import DEBUG

from attr import dataclass
from numpy import inf

from .secret import google_maps_api_key

tomorrow = datetime.today() + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y-%m-%d")


@dataclass
class Config(object):
    log_level = DEBUG
    log_file = None
    url = "https://www.leboncoin.fr/recherche/?category=9&locations=r_16&" \
          "real_estate_type=1&immo_sell_type=old,new&price=min-325000&square=60-max"
    scrap_time = 24  # hours
    headless = False
    output_folder = "/tmp/output"
    start_anonymously = False
    use_proxy = False
    date_filter_field = "index_date"
    google_maps_api_key = google_maps_api_key
    directions = dict(
        boulot_velo=(inf, dict(
            destination="FFLY4U, 3 avenue Didier Daurat Toulouse",
            mode="bicycling",
            arrival_time=datetime.strptime(tomorrow_str + " 9:00:00", '%Y-%m-%d %H:%M:%S').timestamp()
        )),
        boulot_voiture=(30, dict(
            destination="FFLY4U, 3 avenue Didier Daurat Toulouse",
            mode="driving",
            arrival_time=datetime.strptime(tomorrow_str + " 9:00:00", '%Y-%m-%d %H:%M:%S').timestamp()
        ))

    )
