# Description
Ce script python3 permet à partir d'une URL leboncoin de parser toutes les offres et de créer un fichier KML pouvant être ouvert dans google earth contenant les offres des différentes pages.

# Exemples
La commande
```
python3 main.py https://www.leboncoin.fr/informatique/offres/ out.kml -e 10,100 -m 10
```
permet de récupérer les offres informatiques du site jusqu'à la page 10 et fournit un fichier KML `out.kml` en sortie où chaque point est coloré sur une échelle de vert à rouge en fonction du prix (de 10 à 100€)

# Proxy
Vous pouvez utiliser [proxybroker](https://github.com/constverum/ProxyBroker) pour proxifier les requetes