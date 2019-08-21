import logging

import jinja2
import urllib3

logging.getLogger("urllib3").setLevel(logging.WARNING)

headers = {
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0'
}
http = urllib3.PoolManager(headers=headers)
encoding = "utf-8"

get = lambda *args, **kwargs: http.request("GET", *args, **kwargs)

templateLoader = jinja2.FileSystemLoader(searchpath="./")
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
    return id
