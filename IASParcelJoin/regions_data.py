# -*- coding: utf-8 -*-
# Voivodeships (województwa) with their 2-digit TERYT codes, in Polish alphabetical order.
# County (powiat) TERYT codes are 4 digits and start with the voivodeship code.
VOIVODESHIPS = [
    ("02", "Dolnośląskie"),
    ("04", "Kujawsko-pomorskie"),
    ("06", "Lubelskie"),
    ("08", "Lubuskie"),
    ("10", "Łódzkie"),
    ("12", "Małopolskie"),
    ("14", "Mazowieckie"),
    ("16", "Opolskie"),
    ("18", "Podkarpackie"),
    ("20", "Podlaskie"),
    ("22", "Pomorskie"),
    ("24", "Śląskie"),
    ("26", "Świętokrzyskie"),
    ("28", "Warmińsko-mazurskie"),
    ("30", "Wielkopolskie"),
    ("32", "Zachodniopomorskie"),
]

POLISH_ORDER = "aąbcćdeęfghijklłmnńoóprsśtuwyzźż"


def polish_sort_key(text):
    """Sort key that puts Polish letters (ą, ć, ę, ł, ...) right after their base letter."""
    return [POLISH_ORDER.index(c) if c in POLISH_ORDER else 100 + ord(c) for c in text.lower()]
