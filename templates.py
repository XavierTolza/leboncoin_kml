import jinja2

templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)


def get_template(file):
    return templateEnv.get_template(file)
