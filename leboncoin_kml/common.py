import logging
import random
from json import dumps
from os.path import join, dirname, abspath
from urllib.parse import ParseResult, urlencode, parse_qsl, urlparse, unquote
import numpy as np

import jinja2
import urllib3

logging.getLogger("urllib3").setLevel(logging.WARNING)

user_agents = """Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)
Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)
Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.8.1) VoilaBot BETA 1.2 (support.voilabot@orange-ftgroup.com)
Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)
Mozilla/5.0 (Windows NT 5.1; rv:13.0) Gecko/20100101 Firefox/13.0.1
Mozilla/5.0 (Windows NT 5.1; rv:5.0.1) Gecko/20100101 Firefox/5.0.1
Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0
Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.112 Safari/535.1
Mozilla/5.0 (Windows NT 6.0) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.112 Safari/535.1
Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.0) Opera 7.02 Bork-edition [en]
Mozilla/5.0 (Windows NT 6.1; rv:2.0b7pre) Gecko/20100921 Firefox/4.0b7pre
Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322)
Mozilla/5.0 (Linux; U; Android 2.2; fr-fr; Desire_A8181 Build/FRF91) App3leWebKit/53.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1
Mediapartners-Google
magpie-crawler/1.1 (U; Linux amd64; en-GB; +http://www.brandwatch.net)
Mozilla/5.0 (compatible; AhrefsBot/5.0; +http://ahrefs.com/robot/)
Mozilla/5.0 (compatible; Ezooms/1.0; ezooms.bot@gmail.com)
Mozilla/5.0 (compatible; proximic; +http://www.proximic.com/info/spider.php)
Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)
Mozilla/5.0 (compatible; Exabot/3.0; +http://www.exabot.com/go/robot)
Sosospider+(+http://help.soso.com/webspider.htm)
msnbot/2.0b (+http://search.msn.com/msnbot.htm)
Wotbox/2.01 (+http://www.wotbox.com/bot/)
facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)
Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0""".split("\n")

headers = {
    'USER_AGENT': random.choice(user_agents)
}
http = urllib3.PoolManager(headers=headers)
encoding = "utf-8"
N_PROXY = 100
DEFAULT_PROXY_FILE = join(dirname(abspath(__file__)), "assets/proxylist.txt")

get = lambda *args, **kwargs: http.request("GET", *args, **kwargs)
assets_folder = join(dirname(abspath(__file__)), "assets")
templateLoader = jinja2.FileSystemLoader(searchpath=assets_folder)
templateEnv = jinja2.Environment(loader=templateLoader)


def get_template(file):
    return templateEnv.get_template(file)


def supprime_accent(ligne):
    """ supprime les accents du texte source """
    accent = ['é', 'è', 'ê', 'à', 'ù', 'û', 'ç', 'ô', 'î', 'ï', 'â']
    sans_accent = ['e', 'e', 'e', 'a', 'u', 'u', 'c', 'o', 'i', 'i', 'a']
    i = 0
    while i < len(accent):
        ligne = ligne.replace(accent[i], sans_accent[i])
        i += 1
    return ligne


def id_from_url(url):
    id = url.split(".htm")[0].split("/")[-1]
    return int(id)


def add_url_params(url, **params):
    """ Add GET params to provided URL being aware of existing.

    :param url: string of target URL
    :param params: dict containing requested params to be added
    :return: string with updated URL

    >> url = 'http://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> add_url_params(url, new_params)
    'http://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting URL first so we don't loose existing args
    url = unquote(url)
    # Extracting url info
    parsed_url = urlparse(url)
    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query
    # Converting URL arguments to dict
    parsed_get_args = dict(parse_qsl(get_args))
    # Merging URL arguments dict with new params
    parsed_get_args.update(params)

    # Bool and Dict values should be converted to json-friendly values
    # you may throw this part away if you don't like it :)
    parsed_get_args.update(
        {k: dumps(v) for k, v in parsed_get_args.items()
         if isinstance(v, (bool, dict))}
    )

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)
    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme, parsed_url.netloc, parsed_url.path,
        parsed_url.params, encoded_get_args, parsed_url.fragment
    ).geturl()

    return new_url


months = dict(zip("jan,fev,mar,avr,mai,jun,jui,aou,sep,oct,nov,dec".split(","), np.arange(12)+1))
