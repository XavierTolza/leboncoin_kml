import json
from os.path import abspath, join, dirname

from jinja2 import FileSystemLoader, Environment

default_template_folder = join(dirname(abspath(__file__)), "assets")


class HTMLFormatter(object):
    def __init__(self, template_folder=default_template_folder, template_name="report_template.html"):
        self.template_name = template_name
        templateLoader = FileSystemLoader(searchpath=template_folder)
        templateEnv = Environment(loader=templateLoader)
        self.env = templateEnv

    def get_template(self, fname):
        return self.env.get_template(fname)

    def __call__(self, data):
        temp = self.get_template(self.template_name)
        res = temp.render(title="Résultats de la recherche", elements=list(data.values()))
        return res


if __name__ == '__main__':
    with open("data.json", "r") as fp:
        data = json.load(fp)
    res = HTMLFormatter()(data)
    with open("/tmp/out.html", "w") as fp:
        fp.write(res)
    pass
