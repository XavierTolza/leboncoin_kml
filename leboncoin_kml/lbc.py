import re
from datetime import datetime
from json import dumps
from lzma import compress
from time import sleep, time

from googlemaps.exceptions import _OverQueryLimit
from pandas import DataFrame
from selenium.common.exceptions import NoSuchElementException, InsecureCertificateException, \
    UnexpectedAlertPresentException

from leboncoin_kml.annonce import Annonce
from leboncoin_kml.config import Config
from leboncoin_kml.container import Container
from leboncoin_kml.html_encoder import HTMLFormatter
from leboncoin_kml.mail import Sender
from leboncoin_kml.route import Client
from leboncoin_kml.scrapper import Firefox, FindProxyError, ConnexionError


class FinalPageReached(Exception):
    pass


class NeedIdentityChange(Exception):
    pass


class WrongUserAgent(Exception):
    pass


class LBCError(Exception):
    def __init__(self, msg, **info):
        super(LBCError, self).__init__(msg)
        import traceback
        self.trace = traceback.format_exc()
        self.info = dict(trace=self.trace, **info)


class MaximumNumberOfFailures(Exception):
    def __init__(self, last_url, result, n_times):
        super(MaximumNumberOfFailures, self).__init__("Failed to get page %d times" % n_times)
        self.result = result
        self.last_url = last_url


def read_file(filename):
    with open(filename, "rb") as fp:
        res = fp.read()
    return res


class LBC(Firefox):
    def __init__(self, config=Config(), previous_result={}):
        self.config = config
        self.result = previous_result
        self.container = Container(config.output_folder, self.__class__.__name__)
        self.__current_url = config.url
        super(LBC, self).__init__(headless=config.headless, use_proxy_broker=config.use_proxy,
                                  timeout=config.loading_timeout)
        Sender()  # verify user and password for mail
        self.log.info(f"Created LB scrapper with {len(previous_result)} elements in previous result "
                      f"and start url {config.url}")
        self.router = Client(config)

    @property
    def current_lbc_url(self):
        return self.__current_url

    def __enter__(self):
        super(LBC, self).__enter__()
        if self.config.start_anonymously:
            self.log.debug("Waiting for proxy brocker to get proxies")
            while self.broker.data.qsize() < 2:
                sleep(1)
            self.change_identity()
        self.get(self.__current_url)
        return self

    @property
    def need_identity_change(self):
        title = self.title
        blocked_captcha = "blocked" in title
        if self.config.solve_captcha_by_hand:
            while "blocked" in self.title:
                print("Please solve captcha (%i)" % time())
                sleep(5)
        res = blocked_captcha and ("leboncoin" not in title or title == "about:config")
        if res:
            self.log.debug("Need identity change because title is: %s" % title)
        return res

    @property
    def need_user_agent_change(self):
        return "navigateur à jour" in self.title

    @property
    def next_page_link(self):
        try:
            res = self.find_element_by_name("chevronright").find_element_by_xpath("./..").get_attribute("href")
        except NoSuchElementException:
            self.log.warning("Next page not found, trying backup option")
            url = self.__current_url
            match = re.match(".+&page=(\d{1,4})", url)
            if match is None:
                self.log.warning("Failed to find page number in the url, falling back to the third option")
                res = self.find_element_by_css_selector("nav div ul li span").find_element_by_xpath(
                    "./../following::li/a").get_attribute("href")
            else:
                page = int(match.groups()[0])
                res = url.replace("page=%d" % page, "page=%d" % (page + 1))
        return res

    def got_to_next_page(self):
        try:
            url = self.next_page_link
            self.info(f"Moving on to {url}")
            self.__current_url = url
            self.get(url)
        except NoSuchElementException:
            self.info("Final page reached")
            raise FinalPageReached()

    @property
    def list(self):
        data = None
        try:
            data = self.execute_script("return window.__REDIAL_PROPS__;")
            for i in data[::-1]:
                if type(i) == dict and "data" in i and "ads" in i["data"]:
                    return [Annonce(j) for j in i["data"]["ads"]]
            raise ValueError("Failed to find the data in the data container")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise LBCError("Failed finding list of items: %s" % str(e),
                           data=bytes(dumps(data), self.config.encoding),
                           page_source=bytes(self.page_source, self.config.encoding))
        return res

    def get(self, url):
        success = False
        n_try = 0
        while not success:
            try:
                n_try += 1
                if n_try > self.config.maximum_number_retry:
                    self.log.error("Too many failures. Raising exception")
                    raise MaximumNumberOfFailures(self.__current_url, self.result, n_try)
                super(LBC, self).get(url)
                if self.need_identity_change:
                    raise NeedIdentityChange("Felt into captcha")
                if self.need_user_agent_change:
                    raise WrongUserAgent("Need user agent change")
                success = True
            except (NeedIdentityChange, WrongUserAgent,
                    InsecureCertificateException, ConnexionError, FindProxyError, UnexpectedAlertPresentException) as e:
                proxy_change = not issubclass(type(e), WrongUserAgent)
                msg = f"Got error on try {n_try}: {str(e)}. Changing identity"
                if not proxy_change:
                    msg = msg + " only on user agent"
                self.warning(msg)
                self.change_identity(proxy=proxy_change)
            except (IndexError) as e:
                self.log.error(f"Got an unkown error: {e.__class__.__name__} {str(e)}. Retry without identity change")

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
        res = self.result

        try:
            while True:
                self.log.debug("Getting page info")
                annonces = self.list

                n_good_elements = 0
                for i in annonces:
                    date = i.datetime
                    timedelta = (now - date).total_seconds() / (60 * 60)
                    if timedelta > self.config.scrap_time:
                        raise FinalPageReached(f"Time delta ({timedelta}) exceed scrap time ({self.config.scrap_time})")
                    id = str(i["list_id"])
                    keep_record = id not in self.container if self.config.skip_elements_already_in_bdd else True
                    keep_record &= id not in res
                    for filter in self.config.filters:
                        keep_record &= filter(i)
                    self.container[id] = i
                    loc = i["location"]
                    i["directions"] = {}
                    for k, (limit, kwargs) in self.config.directions.items():
                        if not keep_record:
                            break
                        try:
                            directions = self.router.directions(f'{loc["lat"]},{loc["lng"]}', **kwargs)
                            if len(directions) == 0:
                                directions = self.router.directions(f'{loc["city"]}', **kwargs)
                            i["directions"][k] = directions
                            duration = directions[0]["legs"][0]["duration"]["value"] / (60)
                        except (IndexError) as e:
                            self.log.error("Failed to find distance for element "
                                           "%s: %s %s" % (id, e.__class__.__name__, str(e)))
                            duration = 0
                        keep_record &= duration < limit

                    if keep_record:
                        n_good_elements += 1
                        res[id] = i
                timedelta = "%.2f" % timedelta
                self.log.info(f"Parsed {len(annonces)} elements. {n_good_elements} elements passed the filters, "
                              f"{len(res)} elements found so far,"
                              f" the lastest one was posted {timedelta} hours ago")
                self.got_to_next_page()
        except FinalPageReached as e:
            self.log.debug(f"Finishing because catch FinalPageReached: {str(e)}")
        except _OverQueryLimit as e:
            self.log.critical("Google maps API no longer working: %s" % str(e))
        except KeyError as e:
            self.log.critical(f"Aborting parsing: {type(e).__name__}: {str(e)}")

        self.log.info("Finished parsing, sending result")

        if self.config.email_receivers:
            attachments = self.make_attachments(res)
            Sender(self.config)(attachments, body=f"Ci joint, veuillez trouver les {len(res)} annonces du jour qui "
                                                  f"correspondent à vos critères")
        self.log.info("Finished run")

    def make_attachments(self, result):
        attachments = {}

        try:
            attachments["data.json"] = dumps(result)
        except Exception as e:
            self.log.error(f"Failed to add data.json: {type(e).__name__}: {str(e)}")

        try:
            # Formatting final Df
            df = [dict(id=data.id, description=data["body"],
                       date_premiere_publication=data["first_publication_date"],
                       url=data["url"],
                       ville=data.city,
                       map=f'https://www.google.fr/maps/place/{data["location"]["lat"]},{data["location"]["lng"]}',
                       PAP=data["owner"]["no_salesmen"], vendeur=data["owner"]["name"],
                       prix=data["price"][0],
                       title=data["subject"],
                       **{k: v[0]["legs"][0]["duration"]["value"] / 60 for k, v in data["directions"].items()}
                       )
                  for data in (Annonce(data) for id, data in result.items())]
            df = DataFrame(df)
            attachments["data.csv"] = df.to_csv()
        except Exception as e:
            self.log.error(f"Failed to add data.csv: {type(e).__name__}: {str(e)}")

        try:
            html_report = HTMLFormatter()(result)
            attachments["data.html"] = html_report
        except Exception as e:
            self.log.error(f"Failed to add data.html: {type(e).__name__}: {str(e)}")

        try:
            attachments = {k: bytes(v, self.config.encoding) for k, v in attachments.items()}
        except Exception as e:
            self.log.error(f"Failed to convert attachments to bytes")

        try:
            attachments["last_page.html.xz"] = compress(bytes(self.page_source, self.config.encoding))
        except Exception as e:
            self.log.error(f"Failed to add last_page.html.xz: {type(e).__name__}: {str(e)}")

        try:
            log_file = self.config.log_file
            if log_file is not None:
                attachments["log.txt"] = read_file(log_file)
        except Exception as e:
            self.log.error(f"Failed to add log.txt: {type(e).__name__}: {str(e)}")
        return attachments
