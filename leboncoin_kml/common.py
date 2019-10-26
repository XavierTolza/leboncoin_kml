from os.path import join, dirname, abspath

import numpy as np

encoding = "utf-8"
N_PROXY = 100
DEFAULT_PROXY_FILE = join(dirname(abspath(__file__)), "assets/proxylist.txt")

assets_folder = join(dirname(abspath(__file__)), "assets")


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


months = dict(zip("jan,fev,mar,avr,mai,jun,jui,aou,sep,oct,nov,dec".split(","), np.arange(12) + 1))

timeout_settings = "network.dns.resolver_shutdown_timeout_ms," \
                   "network.ftp.idleConnectionTimeout," \
                   "network.http.connection-retry-timeout," \
                   "network.http.keep-alive.timeout," \
                   "network.http.response.timeout," \
                   "network.http.spdy.timeout," \
                   "network.http.tls-handshake-timeout," \
                   "network.proxy.failover_timeout," \
                   "network.tcp.tcp_fastopen_http_stalls_timeout," \
                   "network.trr.request-timeout," \
                   "network.websocket.timeout.close," \
                   "network.http.connection-timeout," \
                   "network.websocket.timeout.open".split(",")
