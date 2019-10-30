from datetime import datetime

from googlemaps import Client
from selenium.common.exceptions import NoSuchElementException, InsecureCertificateException

from leboncoin_kml.config import Config
from leboncoin_kml.container import Container
from leboncoin_kml.scrapper import Firefox, FindProxyError, ConnexionError


class FinalPageReached(Exception):
    pass


class NeedIdentityChange(Exception):
    pass


class WrongUserAgent(Exception):
    pass


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
                if proxy_change:
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
            self.log.info(f"Parsed {len(annonces)} elements")

            for i in annonces:
                date = datetime.strptime(i[self.config.date_filter_field], '%Y-%m-%d %H:%M:%S')
                timedelta = (now - date).total_seconds() / (60 * 60)
                if timedelta > self.config.scrap_time:
                    finished = True
                    break
                id = i["list_id"]
                self.container[id] = i
                loc = i["location"]
                i["directions"] = {}
                distance_correct = True
                for k, (limit, kwargs) in self.config.directions.items():
                    directions = gmap.directions(f'{loc["lat"]},{loc["lng"]}', **kwargs)
                    i["directions"][k] = directions
                    duration = directions[0]["legs"][0]["duration"]["value"] / (60)
                    distance_correct &= duration < limit

                if distance_correct:
                    res[id] = i

            self.got_to_next_page()
