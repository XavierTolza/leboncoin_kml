from datetime import datetime
from json import dumps

from googlemaps import Client
from pandas import DataFrame
from selenium.common.exceptions import NoSuchElementException, InsecureCertificateException

from leboncoin_kml.config import Config
from leboncoin_kml.container import Container
from leboncoin_kml.mail import Sender
from leboncoin_kml.scrapper import Firefox, FindProxyError, ConnexionError


class FinalPageReached(Exception):
    pass


class NeedIdentityChange(Exception):
    pass


class WrongUserAgent(Exception):
    pass


def read_file(filename):
    with open(filename, "rb") as fp:
        res = fp.read()
    return res


class LBC(Firefox):
    def __init__(self, config=Config()):
        super(LBC, self).__init__(headless=config.headless, use_proxy_broker=config.use_proxy)
        self.config = config
        self.container = Container(config.output_folder, self.__class__.__name__)
        self.__current_url = config.url

    def __enter__(self):
        super(LBC, self).__enter__()
        if self.config.start_anonymously:
            self.change_identity()
        self.get(self.config.url)
        return self

    @property
    def need_identity_change(self):
        return "blocked" in self.title

    @property
    def need_user_agent_change(self):
        return "navigateur à jour" in self.title

    @property
    def next_page_link(self):
        res = self.find_element_by_name("chevronright").find_element_by_xpath("./..")
        return res

    def got_to_next_page(self):
        try:
            link = self.next_page_link
            url = link.get_attribute("href")
            self.get(url)
            self.__current_url = url
        except NoSuchElementException:
            raise FinalPageReached()

    @property
    def list(self):
        data = self.execute_script("return window.__REDIAL_PROPS__;")
        res = data[4]["data"]["ads"]
        return res

    def get(self, url):
        success = False
        n_try = 0
        while not success:
            try:
                n_try += 1
                super(LBC, self).get(url)
                if self.need_identity_change:
                    raise NeedIdentityChange("Felt into captcha")
                if self.need_user_agent_change:
                    raise WrongUserAgent("Need user agent change")
                success = True
            except (NeedIdentityChange, WrongUserAgent,
                    InsecureCertificateException, ConnexionError, FindProxyError) as e:
                proxy_change = not issubclass(type(e), WrongUserAgent)
                msg = f"Got error on try {n_try}: {str(e)}. Changing identity"
                if not proxy_change:
                    msg = msg + " only on user agent"
                self.warning(msg)
                self.change_identity(proxy=proxy_change)

    def set_proxy(self, *args, **kwargs):
        super(LBC, self).set_proxy(*args, **kwargs)
        self.log.info(f"Setting proxy {(args, kwargs)}")

    def set_user_agent(self, value):
        super(LBC, self).set_user_agent(value)
        self.log.info(f"Setting user agent: {value}")

    def refresh(self):
        url = self.__current_url
        self.get(url)

    def run(self):
        now = datetime.now()
        finished = False
        gmap = Client(self.config.google_maps_api_key)
        res = {}

        while not finished:
            self.log.debug("Getting page info")
            annonces = self.list

            n_good_elements=0
            for i in annonces:
                date = datetime.strptime(i[self.config.date_filter_field], '%Y-%m-%d %H:%M:%S')
                timedelta = (now - date).total_seconds() / (60 * 60)
                if timedelta > self.config.scrap_time:
                    finished = True
                    break
                id = i["list_id"]
                keep_record = id not in self.container
                self.container[id] = i
                loc = i["location"]
                i["directions"] = {}
                for k, (limit, kwargs) in self.config.directions.items():
                    if not keep_record:
                        break
                    directions = gmap.directions(f'{loc["lat"]},{loc["lng"]}', **kwargs)
                    if len(directions) == 0:
                        directions = gmap.directions(f'{loc["city"]}', **kwargs)
                    i["directions"][k] = directions
                    try:
                        duration = directions[0]["legs"][0]["duration"]["value"] / (60)
                    except IndexError:
                        duration = 0
                    keep_record &= duration < limit

                if keep_record:
                    n_good_elements += 1
                    res[id] = i

            self.log.info(f"Parsed {len(annonces)} elements. {n_good_elements} elements passed the filters,"
                          f" the lastest one was posted %.0f hours ago" % timedelta)
            self.got_to_next_page()

        self.log.info("Finished parsing, sending result")

        # Formatting final Df
        df = [dict(id=id, description=data["body"],
                   date_premiere_publication=data["first_publication_date"],
                   url=data["url"],
                   ville=data["location"]["city"],
                   map=f'https://www.google.fr/maps/place/{data["location"]["lat"]},{data["location"]["lng"]}',
                   PAP=data["owner"]["no_salesmen"], vendeur=data["owner"]["name"],
                   prix=data["price"][0],
                   title=data["subject"],
                   **{k: v[0]["legs"][0]["duration"]["value"] / 60 for k, v in data["directions"].items()}
                   )
              for id, data in res.items()]
        df = DataFrame(df)

        attachments = {"data.json": dumps(res), "data.csv": df.to_csv()}
        attachments = {k: bytes(v, self.config.encoding) for k, v in attachments.items()}
        log_file = self.config.log_file
        if log_file is not None:
            attachments["log.txt"] = read_file(log_file)

        Sender(self.config)(attachments)
        self.log.info("Finished run")
