import pandas as pd
from os.path import isfile, abspath, dirname, join

from leboncoin_kml.common import get

url = "https://www.data.gouv.fr/fr/datasets/r/554590ab-ae62-40ac-8353-ee75162c05ee"

filename = "assets/postal_code_db.csv"
filename = join(dirname(abspath(__file__)), filename)
if isfile(filename):
    db = pd.read_csv(filename).set_index("Unnamed: 0")
else:
    from io import StringIO

    print("Download postal code database. Please wait")
    db = get(url).data
    db = pd.read_csv(StringIO(db.decode("utf-8")), sep=";")
    db = db.rename(dict(Nom_commune="nom", Code_postal="code", coordonnees_gps="gps"), axis=1)
    db = db["nom,code,gps".split(",")]
    db.to_csv(filename)
