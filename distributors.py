"""
distributors.py: Listas de clasificación de distribuidoras (copia autocontenida).

Bundleada dentro del proyecto para que NO dependa de ningún repo externo. Si actualizás
las listas en el repo principal (config/distributors.py), sincronizá acá.

Todos los valores en minúsculas y sin tildes (comparación vía _normalize en parser).
"""

DIY_DISTRIBUTORS = {
    "distrokid", "tunecore", "cdbaby", "amuse", "unitedmasters", "united masters",
    "routenote", "ditto music", "lanzadera", "offstep", "tustreams", "la flota",
    "audio killers", "sua musica", "symphonic", "igroove", "proton", "iip-dds",
    "puro digital", "2btube", "yt rocket", "tritono", "kog chief", "vydia",
    "naeku", "bhavilonia", "valle de los reyes",
}

DIFICIL_DISTRIBUTORS = {
    "onerpm", "farolatino", "label engine", "awal", "top media", "cinq music",
    "colonize media", "digital music marketing", "dbn", "label worx", "amp suite",
    "kontor new media", "divucsa", "cr2 records", "naxos", "plaza independencia",
    "garra records", "disetti", "mona records", "dale q", "arietta distro",
    "huracan records", "wolfclan", "discos horoscopo", "tlp records",
    "indyana records", "paral records", "mawz records", "everlasting records",
    "codiscos", "nes music", "grupo cali", "grupo celeste", "sonkora", "fumaratto",
    "keymer disc", "casete upload", "dinastia", "creation music", "club29",
    "one blood", "big sound", "chule productions", "syskon music", "ocho music",
    "previa & fiesta", "espantapajaros", "piloto producciones", "xelon entertainment",
    "puro music non-family", "urban club", "dj alex", "pschent music",
    "la sonora dinamita", "leader euro music", "leader music", "onda sabanera",
    "discos elio", "hyphy", "tango multimedia", "emporio records", "toy cantando",
    "discos migue", "delirio valdez", "microfon", "dynamo", "5020 records",
}

DIFICIL_DISTRIBUTORS_EXACT = {"isis", "gote", "1.8m", "non-family"}

DISTRIBUTOR_BLACKLIST = {
    "the orchard", "orchard enterprises", "universal music", "sony music",
    "wm chile", "wm spain", "wm mexico", "wm argentina", "wea latina",
    "warner music", "atlantic records", "legacy recordings", "virgin music",
    "rca victor", "rca records", "columbia records", "columbia", "epic records",
    "epic", "arista", "csv2ddex", "adshare",
}
