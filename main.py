import logging
from argparse import ArgumentParser
from os import mkdir
from os.path import abspath, dirname, join, isdir

from scrapy.crawler import CrawlerProcess

from leboncoin_kml.common import headers
from leboncoin_kml.scrapper import LBCScrapper

logging.getLogger("scrapy").setLevel(logging.WARNING)
logging.getLogger("scrapy.core.engine").setLevel(logging.WARNING)


def scrap(url, out_file, echelle, max_page, use_proxy):
    settings = dict(LOG_LEVEL="DEBUG", CONCURRENT_REQUESTS=1000, CONCURRENT_REQUESTS_PER_DOMAIN=1000,
                    CONCURRENT_REQUESTS_PER_IP=1000, CONCURRENT_ITEMS=1000, **headers)
    if use_proxy:
        settings["DOWNLOADER_MIDDLEWARES"] = {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'proxy.RandomProxy': 100,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
        settings.update(dict(PROXY_LIST='proxylist.txt',
                             PROXY_MODE=1, RETRY_ENABLED=True,
                             RETRY_TIMES=10, RETRY_HTTP_CODES=[500, 503, 504, 400, 403, 404, 408]))

    images_folder = join(dirname(abspath(out_file)), "images")
    if not isdir(images_folder):
        mkdir(images_folder)

    process = CrawlerProcess(settings)

    process.crawl(LBCScrapper, url, out_file, images_folder, max_page)
    process.start()  # the script will block here until the crawling is finished


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("url", help="URL de départ sur le site leboncoin.")
    parser.add_argument("out_file", help="Fichier KML de sortie", default="out.kml")
    parser.add_argument("--echelle_prix", "-e", dest="echelle",
                        help="Echelle de prix pour afficher le prix comme une couleur de point dans le KML",
                        default=None, type=lambda x: [int(i) for i in x.split(",")])
    parser.add_argument("-m", dest="max_page", help="Page max", default=None, type=int)
    parser.add_argument("--use_proxy", "-p", action="store_true", help="Use tor proxy")

    args = parser.parse_args()
    scrap(**args.__dict__)
