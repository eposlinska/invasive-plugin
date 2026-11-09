# -*- coding: utf-8 -*-
# Generated from species.csv, filtered to species on the IGO lists (Union list and/or
# Polish list). Layer number = openedAddSelection value, WFS type name = 'ias:gatunek<number>'.
# (layer_number, polish_name, latin_name, invasiveness, spread, category)
# category is 'plants' or 'animals' (assigned by genus in the generator).
CATEGORIES = [('plants', 'Rośliny'), ('animals', 'Zwierzęta')]

# Which IGO list a layer comes from: 'UE' = threat to the Union, 'PL' = threat to Poland.
IGO_LIST = {
    13: 'PL',
    16: 'PL',
    21: 'UE',
    23: 'UE',
    24: 'PL',
    27: 'UE',
    30: 'UE',
    36: 'UE',
    39: 'UE',
    41: 'UE+PL',
    43: 'UE',
    45: 'UE',
    47: 'UE',
    48: 'PL',
    50: 'PL',
    51: 'UE',
    60: 'UE',
    67: 'UE',
    68: 'PL',
    69: 'UE',
    70: 'UE',
    76: 'UE',
    78: 'UE',
    79: 'UE',
    80: 'UE',
    81: 'UE',
    82: 'UE+PL',
    83: 'UE+PL',
    84: 'UE+PL',
    92: 'UE',
    94: 'PL',
    96: 'UE',
    101: 'UE',
    102: 'UE',
    111: 'UE',
    115: 'PL',
    116: 'PL',
    117: 'PL',
    118: 'UE',
    360: 'UE',
}

# Group within the list: 'eradication' = podlegające szybkiej eliminacji,
# 'widespread' = rozprzestrzenione na szeroką skalę. Species missing here have no known group.
STATUS_LABELS = [('eradication', 'Szybka eliminacja'), ('widespread', 'Rozprzestrzenione na szeroką skalę')]
STATUS = {
    16: 'widespread',  # Azolla filiculoides - named (Polish list)
    21: 'widespread',  # Heracleum mantegazzianum - named (Union list)
    23: 'widespread',  # Heracleum sosnowskyi - named (Union list)
    24: 'eradication',  # Branta canadensis - named (Polish list)
    27: 'widespread',  # Ailanthus altissima - named (Union list)
    13: 'widespread',  # Corbicula fluminea - named (Polish list)
    30: 'widespread',  # Pseudorasbora parva - named (Union list)
    360: 'widespread',  # Celastrus orbiculatus - named (Union list)
    36: 'eradication',  # Alopochen aegyptiacus - INFERRED (Union list, not named as widely spread)
    39: 'eradication',  # Threskiornis aethiopicus - INFERRED (Union list, not named as widely spread)
    41: 'eradication',  # Cervus nippon - named (Polish list)
    43: 'widespread',  # Nyctereutes procyonoides - named (Union list)
    45: 'eradication',  # Cabomba caroliniana - INFERRED (Union list, not named as widely spread)
    47: 'eradication',  # Nasua nasua - INFERRED (Union list, not named as widely spread)
    48: 'widespread',  # Ulex europaeus - named (Polish list)
    50: 'widespread',  # Echinocystis lobata - named (Polish list)
    51: 'widespread',  # Eriocheir sinensis - named (Union list)
    60: 'widespread',  # Elodea nuttallii - named (Union list)
    67: 'widespread',  # Impatiens glandulifera - named (Union list)
    68: 'widespread',  # Impatiens capensis - named (Polish list)
    70: 'eradication',  # Myocastor coypus - INFERRED (Union list, not named as widely spread)
    76: 'widespread',  # Ondatra zibethicus - named (Union list)
    78: 'eradication',  # Procambarus clarkii - INFERRED (Union list, not named as widely spread)
    79: 'widespread',  # Procambarus fallax f. virginalis - named (Union list)
    80: 'widespread',  # Orconectes limosus - named (Union list)
    81: 'widespread',  # Pacifastacus leniusculus - named (Union list)
    82: 'widespread',  # Reynoutria x bohemica - named (Polish list)
    83: 'widespread',  # Reynoutria japonica - named (Polish list)
    84: 'widespread',  # Reynoutria sachalinensis - named (Polish list)
    92: 'eradication',  # Oxyura jamaicensis - INFERRED (Union list, not named as widely spread)
    94: 'widespread',  # Ameiurus nebulosus - named (Polish list)
    96: 'widespread',  # Procyon lotor - named (Union list)
    101: 'widespread',  # Perccottus glenii - named (Union list)
    102: 'widespread',  # Asclepias syriaca - named (Union list)
    69: 'widespread',  #Neovison vison - named (Union list)
    111: 'eradication',  # Corvus splendens - INFERRED (Union list, not named as widely spread)
    115: 'eradication',  # Chelydra serpentina - named (Polish list)
    116: 'eradication',  # Chrysemys picta - named (Polish list)
    117: 'eradication',  # Graptemys pseudogeographica - named (Polish list)
    118: 'widespread',  # Trachemys scripta - named (Union list)
}

SPECIES = [
    (16, 'Azolla drobna', 'Azolla filiculoides', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (21, 'Barszcz Mantegazziego', 'Heracleum mantegazzianum', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (23, 'Barszcz Sosnowskiego', 'Heracleum sosnowskyi', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (24, 'Bernikla kanadyjska', 'Branta canadensis', 'bardzo inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (27, 'Bożodrzew gruczołowaty', 'Ailanthus altissima', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (13, '', 'Corbicula fluminea', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (30, 'Czebaczek amurski', 'Pseudorasbora parva', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (360, 'Dławisz okrągłolistny', 'Celastrus orbiculatus', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (36, 'Gęsiówka egipska', 'Alopochen aegyptiacus', 'bardzo inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (39, 'Ibis czczony', 'Threskiornis aethiopicus', 'mało inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (41, 'Jeleń sika', 'Cervus nippon', 'bardzo inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (43, 'Jenot', 'Nyctereutes procyonoides', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (45, 'Kabomba karolińska', 'Cabomba caroliniana', 'bardzo inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (47, 'Koati', 'Nasua nasua', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (48, 'Kolcolist zachodni', 'Ulex europaeus', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (50, 'Kolczurka klapowana', 'Echinocystis lobata', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (51, 'Krab wełnistoręki', 'Eriocheir sinensis', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (60, 'Moczarka delikatna', 'Elodea nuttallii', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (67, 'Niecierpek gruczołowaty', 'Impatiens glandulifera', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (68, 'Niecierpek pomarańczowy', 'Impatiens capensis', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (70, 'Nutria', 'Myocastor coypus', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (76, 'Piżmak', 'Ondatra zibethicus', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (78, 'Rak luizjański', 'Procambarus clarkii', 'bardzo inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (79, 'Rak marmurkowy', 'Procambarus fallax f. virginalis', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (80, 'Rak pręgowany', 'Orconectes limosus', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (81, 'Rak sygnałowy', 'Pacifastacus leniusculus', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'animals'),
    (82, 'Rdestowiec czeski', 'Reynoutria x bohemica', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (83, 'Rdestowiec japoński', 'Reynoutria japonica', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (84, 'Rdestowiec sachaliński', 'Reynoutria sachalinensis', 'bardzo inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'plants'),
    (92, 'Sterniczka jamajska', 'Oxyura jamaicensis', 'mało inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (94, 'Sumik karłowaty', 'Ameiurus nebulosus', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (96, 'Szop pracz', 'Procyon lotor', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (101, 'Trawianka', 'Perccottus glenii', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (102, 'Trojeść amerykańska', 'Asclepias syriaca', 'mało inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'plants'),
    (69, 'Wizon amerykański', 'Neovison vison', 'średnio inwazyjny gatunek obcy', 'gatunek szeroko rozprzestrzeniony', 'animals'),
    (111, 'Wrona orientalna', 'Corvus splendens', 'bardzo inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (115, 'Żółw jaszczurowaty', 'Chelydra serpentina', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (116, 'Żółw malowany', 'Chrysemys picta', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (117, 'Żółw ostrogrzbiety', 'Graptemys pseudogeographica', 'średnio inwazyjny gatunek obcy', 'populacja(e) izolowana(e)', 'animals'),
    (118, 'Żółw ozdobny', 'Trachemys scripta', 'średnio inwazyjny gatunek obcy', 'ograniczony zasięg występowania', 'animals'),
]
