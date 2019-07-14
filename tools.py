def supprime_accent(ligne):
    """ supprime les accents du texte source """
    accent = ['é', 'è', 'ê', 'à', 'ù', 'û', 'ç', 'ô', 'î', 'ï', 'â']
    sans_accent = ['e', 'e', 'e', 'a', 'u', 'u', 'c', 'o', 'i', 'i', 'a']
    i = 0
    while i < len(accent):
        ligne = ligne.replace(accent[i], sans_accent[i])
        i += 1
    return ligne