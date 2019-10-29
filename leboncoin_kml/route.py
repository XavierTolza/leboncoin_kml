import requests


class OSMR(object):
    def __init__(self, server_url, server_version=1):
        self.server_version = server_version
        self.server_url = server_url

    def __call__(self, start_point, stop_point, mode="car"):
        url = f'{self.server_url}/route/v{self.server_version}/{mode}/' \
            f'{start_point[0]},{start_point[1]};{stop_point[0]},{stop_point[1]}?overview=false'
        res = requests.get(url)
        res = res.json()
        return res


if __name__ == '__main__':
    o = OSMR("http://router.project-osrm.org")
    res = o((43.549413, 1.506329), (43.563323, 1.491030))
    pass
