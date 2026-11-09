import csv
import datetime
import json
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import urlencode

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QUrl, QVariant
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QProgressDialog
from qgis.core import (
    NULL,
    Qgis,
    QgsApplication,
    QgsBlockingNetworkRequest,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsMessageLog,
    QgsProject,
    QgsRectangle,
    QgsSettings,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .regions_data import VOIVODESHIPS, polish_sort_key
# SPECIES rows: (layer_number, polish, latin, invasiveness, spread, category)
from .species_data import CATEGORIES, IGO_LIST, SPECIES, STATUS, STATUS_LABELS
try:
    from .xlsx_writer import write_xlsx
except ImportError:  # xlsx_writer.py not copied to the plugin folder: CSV still works
    write_xlsx = None

LOG_TAG = "IAS Parcel Join"
CRS_PL = "EPSG:2180"

# --- IAS (GDOŚ) -------------------------------------------------------
WFS_URL = "https://inwazyjne.gdos.gov.pl/geoserver/wfs"
WFS_PREFIX = "ias"  # layer type name = f"{WFS_PREFIX}:gatunek{layer_number}"

# Only objects that have a value in ALL of these fields are kept.
REQUIRED_FIELDS = ("nrrej",)

# Ask the server only for objects inside the selected area's bounding box (much faster than the
# whole country). If an area unexpectedly returns 0 objects, set this to False to test.
USE_SERVER_BBOX = True

# IAS attributes copied into the report: logical name -> candidate field names (lower case).
# Names are taken from the first version of the plugin and are UNVERIFIED; a missing field gives a blank column.
IAS_REPORT_FIELDS = {
    "nrrej": ("nrrej",),
    "min": ("liczebnoscmin",),
    "max": ("liczebnoscmax",),
    "unit": ("jednostkaliczebnosci", "jednostka"),
    "date": ("datastwierdzenia",),
}

# --- PRG (GUGiK administrative boundaries) -----------------------------
PRG_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/PRG/WFS/AdministrativeBoundaries"
# County layer. The fallback is UNVERIFIED; the real name is discovered from GetCapabilities
# (any type with "powiat"). Field names are matched case-insensitively against the real fields.
PRG_COUNTY_FALLBACK = "ms:A02_Granice_powiatow"
PRG_CODE_FIELDS = ("JPT_KOD_JE", "KOD_JE", "TERYT")   # county TERYT code (4 digits)
PRG_NAME_FIELDS = ("JPT_NAZWA_", "NAZWA")             # county name

# Commune layer. Same approach (discovered by "gmin" in the name). UNVERIFIED fallback and fields.
PRG_COMMUNE_FALLBACK = "ms:A03_Granice_gmin"
PRG_COMMUNE_CODE_FIELDS = ("JPT_KOD_JE", "KOD_JE", "TERYT")   # commune TERYT code (7 digits, the first 4 = county code)
PRG_COMMUNE_NAME_FIELDS = ("JPT_NAZWA_", "NAZWA")             # commune name

CACHE_FILE = "counties_cache.json"          # county lists are saved here after the first download
CACHE_FILE_COMMUNE = "communes_cache.json"  # commune lists likewise (delete the file to refresh)

WHOLE_COUNTY = "(cały powiat)"
# 7th digit of a commune's TERYT code
COMMUNE_TYPES = {"1": "miejska", "2": "wiejska", "3": "miejsko-wiejska"}

# What differs between the two PRG boundary layers
PRG_KINDS = {
    "county": {
        "keyword": "powiat", "fallback": PRG_COUNTY_FALLBACK,
        "code_fields": PRG_CODE_FIELDS, "name_fields": PRG_NAME_FIELDS,
        "layer_label": "powiaty", "plural": "powiatów", "singular": "powiatu",
    },
    "commune": {
        "keyword": "gmin", "fallback": PRG_COMMUNE_FALLBACK,
        "code_fields": PRG_COMMUNE_CODE_FIELDS, "name_fields": PRG_COMMUNE_NAME_FIELDS,
        "layer_label": "gminy", "plural": "gmin", "singular": "gminy",
    },
}

# --- EGiB parcels (GUGiK) ---------------------------------------------------
EGIB_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/EGIB/WFS/UslugaZbiorcza"
EGIB_TYPENAME = "ms:dzialki"
# logical name -> candidate field names (matched case-insensitively); from the service's DescribeFeatureType
CUSTOM_ID_FIELDS = ("IDDZIALKI", "TERYT", "ID_DZ", "IDENT")  # extra names for a user's own parcel layer
PARCEL_FIELDS = {
    "id": ("ID_DZIALKI",),
    "number": ("NUMER_DZIALKI",),
    "precinct": ("NAZWA_OBREBU",),
    "precinct_no": ("NUMER_OBREBU",),
    "commune": ("NAZWA_GMINY",),
    "area": ("POLE_EWIDENYJNE", "POLE_EWIDENCYJNE"),
}
# Parcels are requested in square cells of this size (metres, EPSG:2180): few requests, each small.
PARCEL_CELL_M = 2000  # bigger cells = far fewer requests; the commune filter keeps them light
# A polygon that only grazes a parcel (overlap below this, m²) is not reported for that parcel,
# unless no parcel has a bigger overlap.
MIN_OVERLAP_M2 = 1.0

REPORT_HEADER = [
    "Gmina", "Powiat", "Gatunek", "Nazwa łacińska", "Lista", "Status",
    "Nr rejestracyjny (nrrej)", "Typ obiektu", "Liczebność min", "Liczebność max", "Jednostka",
    "Data stwierdzenia", "ID działki", "Nr działki", "Obręb", "Nr obrębu", "Gmina (EGiB)",
    "Pole ewidencyjne działki", "Pow. obiektu w działce [m²]", "WKT obiektu (EPSG:2180)",
]
PARCEL_WKT_HEADER = ["ID działki", "Nr działki", "Obręb", "Nr obrębu", "Gmina (EGiB)", "WKT działki (EPSG:2180)"]
WKT_CELL_LIMIT = 32000   # Excel refuses cells over 32767 characters
SUMMARY_HEADER = ["Gatunek", "Nazwa łacińska", "Lista", "Status", "Liczba obiektów",
                  "Liczba działek", "Obiekty bez działki", "Uwagi"]
STATUS_NAMES = dict(STATUS_LABELS)
SPECIES_BY_NUMBER = {s[0]: s for s in SPECIES}


class _Canceled(Exception):
    """The user pressed Cancel in the progress dialog."""


def _is_missing(value):
    """True for None, SQL NULL and empty/blank strings."""
    if value is None or value == NULL:
        return True
    return isinstance(value, str) and not value.strip()


def _plain(value):
    """Value for a report cell: '' for missing values, ISO text for dates."""
    if _is_missing(value):
        return ""
    if hasattr(value, "toString"):      # QDate / QDateTime
        return value.toString(Qt.ISODate)
    return value


def _label_communes(rows):
    """[(code, name), ...] -> [(code, label), ...].

    Names that occur more than once inside a county (for example a town and the rural commune
    around it) get their type appended, so the user can tell them apart.
    """
    counts = Counter(name for _code, name in rows)
    out = []
    for code, name in rows:
        label = name
        if counts[name] > 1:
            kind = COMMUNE_TYPES.get(code[6:7])
            label = f"{name} ({kind})" if kind else f"{name} ({code})"
        out.append((code, label))
    return out


def _pick_communes(g, communes, is_point):
    """Find the commune(s) an object lies in.

    `communes` is a list of dicts with "engine" (prepared geometry engine) and "geom".
    Returns (best, others): `best` is the commune containing a point, or for a polygon the one
    with the largest overlap; `others` are further communes the object touches (it lies on a
    border). `best` is None when no commune matches.
    """
    hits = [c for c in communes if c["engine"].intersects(g.constGet())]
    if not hits:
        return None, []
    if len(hits) == 1 or is_point:
        return hits[0], hits[1:]

    def overlap(c):
        inter = g.intersection(c["geom"])
        return 0.0 if inter is None or inter.isNull() else inter.area()

    hits.sort(key=overlap, reverse=True)
    return hits[0], hits[1:]


def _grid_cells(xmin, ymin, xmax, ymax, size):
    """(ix, iy) of every grid cell of side `size` touched by the bounding box."""
    ix0, ix1 = math.floor(xmin / size), math.floor(xmax / size)
    iy0, iy1 = math.floor(ymin / size), math.floor(ymax / size)
    return [(ix, iy) for ix in range(ix0, ix1 + 1) for iy in range(iy0, iy1 + 1)]


def _cell_rect(cell, size=PARCEL_CELL_M):
    ix, iy = cell
    return QgsRectangle(ix * size, iy * size, (ix + 1) * size, (iy + 1) * size)


def _wkt(g):
    """WKT of a geometry (metres, 2 decimals), simplified if it would not fit one Excel cell."""
    if g is None or g.isNull():
        return ""
    text = g.asWkt(2)
    tolerance = 0.5
    while len(text) > WKT_CELL_LIMIT and tolerance <= 64:
        simple = g.simplify(tolerance)
        if simple is not None and not simple.isNull():
            text = simple.asWkt(2)
        tolerance *= 2
    return text if len(text) <= WKT_CELL_LIMIT else text[:WKT_CELL_LIMIT]


def _match_parcels(g, is_point, index, parcels):
    """Parcels an object lies on: [(parcel, overlap_m2 or None), ...], biggest overlap first.

    `index.intersects(rect)` gives candidate parcel ids, `parcels[id]["geom"]` the boundaries.
    A point belongs to the parcel(s) containing it. A polygon belongs to every parcel it overlaps
    by at least MIN_OVERLAP_M2 (or, failing that, to the one with the biggest overlap).
    """
    hits = []
    for pid in index.intersects(g.boundingBox()):
        parcel = parcels[pid]
        if not parcel["geom"].intersects(g):
            continue
        if is_point:
            hits.append((parcel, None))
            continue
        inter = g.intersection(parcel["geom"])
        hits.append((parcel, 0.0 if inter is None or inter.isNull() else inter.area()))
    if is_point or not hits:
        return hits
    big = [h for h in hits if h[1] >= MIN_OVERLAP_M2]
    big = big or [max(hits, key=lambda h: h[1])]
    return sorted(big, key=lambda h: -h[1])


def _ias_columns(field_names):
    """logical report column -> index in the IAS layer's fields (or None if the layer has no such field)."""
    lower = {n.lower(): i for i, n in enumerate(field_names)}
    return {key: next((lower[c] for c in cands if c in lower), None)
            for key, cands in IAS_REPORT_FIELDS.items()}


def _safe_filename(text):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "raport"


class IASParcelJoin:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dialog = uic.loadUi(os.path.join(self.plugin_dir, "gui.ui"))

        needed = ("categoryBox", "statusBox", "speciesBox", "voivodeshipBox", "countyBox",
                  "communeBox", "downloadIASButton", "reportButton", "modeLayerRadio",
                  "modeReportRadio", "parcelLayerLabel", "parcelLayerBox")
        missing = [n for n in needed if not hasattr(self.dialog, n)]
        if missing:
            raise RuntimeError("gui.ui is out of date, missing widgets: " + ", ".join(missing))

        self._county_cache = self._load_cache(CACHE_FILE)
        self._commune_cache = self._load_cache(CACHE_FILE_COMMUNE)
        self._prg_feature_types = None
        self._prg_typenames = {}
        self._errors = None  # when a list: warnings are collected instead of shown one by one

        # Which bbox axis order the IAS server accepts is learned once and remembered between sessions.
        learned = QgsSettings().value("IASParcelJoin/bboxMode", "")
        self._bbox_mode = learned if learned in ("xy", "yx") else None

        # Connect signals ONCE (connecting inside run() stacks connections).
        self.dialog.downloadIASButton.clicked.connect(self.onDownloadIAS)
        self.dialog.reportButton.clicked.connect(self.onReport)
        self.dialog.modeLayerRadio.toggled.connect(self._apply_mode)
        self._apply_mode()

        # Category (plants / animals) and status (quick eradication / widely spread) -> species
        self.dialog.categoryBox.addItem("(wszystkie)", None)
        for key, label in CATEGORIES:
            self.dialog.categoryBox.addItem(label, key)
        self.dialog.statusBox.addItem("(wszystkie)", None)
        for key, label in STATUS_LABELS:
            self.dialog.statusBox.addItem(label, key)
        self.dialog.categoryBox.currentIndexChanged.connect(self._fill_species)
        self.dialog.statusBox.currentIndexChanged.connect(self._fill_species)
        self._fill_species()

        # Voivodeship (static, instant) -> counties (loaded on demand, then cached)
        #   -> communes (loaded on demand, then cached)
        for code, name in VOIVODESHIPS:
            self.dialog.voivodeshipBox.addItem(name, code)
        self.dialog.voivodeshipBox.currentIndexChanged.connect(self._fill_counties)
        self.dialog.countyBox.currentIndexChanged.connect(self._fill_communes)
        self._fill_communes()  # starts with just "(cały powiat)"; no network needed

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, "IAS Parcel Join", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&IAS Parcel Join", self.action)

    def unload(self):
        self.iface.removePluginMenu("&IAS Parcel Join", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # Load the county list on first open (not at QGIS start-up, which would need network).
        if self.dialog.countyBox.count() == 0:
            self._fill_counties()
        self.dialog.exec_()

    def _fill_parcel_layers(self):
        """Polygon layers of the current project that can serve as the parcel source."""
        box = self.dialog.parcelLayerBox
        previous = box.currentData()
        box.blockSignals(True)
        box.clear()
        box.addItem("(pobierz z EGiB)", None)
        for layer in QgsProject.instance().mapLayers().values():
            if (isinstance(layer, QgsVectorLayer) and layer.isValid()
                    and layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                box.addItem(layer.name(), layer.id())
        i = box.findData(previous)
        box.setCurrentIndex(max(i, 0))
        box.blockSignals(False)

    def _apply_mode(self, *_args):
        """One species layer (default) or a whole-commune report: show only what that mode needs."""
        d = self.dialog
        report = d.modeReportRadio.isChecked()
        for w in (d.speciesLabel, d.speciesBox, d.downloadIASButton):
            w.setVisible(not report)
        for w in (d.parcelLayerLabel, d.parcelLayerBox, d.reportButton):
            w.setVisible(report)
        if report:
            self._fill_parcel_layers()
        d.communeLabel.setText("Gmina (wymagana)" if report else "Gmina")

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _warn(self, text):
        self._log(text, Qgis.Critical)
        if self._errors is not None:          # report run: collect, summarise at the end
            self._errors.append(text)
            return
        self.iface.messageBar().pushMessage("Błąd", text, level=Qgis.Critical)

    def _log(self, text, level=Qgis.Info):
        QgsMessageLog.logMessage(text, LOG_TAG, level)

    def _fill_species(self, *_args):
        category = self.dialog.categoryBox.currentData()   # None = all
        status = self.dialog.statusBox.currentData()       # None = all
        box = self.dialog.speciesBox
        box.clear()
        for number, polish, latin, _invasive, _spread, cat in SPECIES:
            if category is not None and cat != category:
                continue
            if status is not None and STATUS.get(number) != status:
                continue
            label = f"{polish} ({latin})" if polish else latin
            box.addItem(label, number)  # layer number is stored as item data

    # ------------------------------------------------------------------
    # PRG boundaries (counties and communes)
    # ------------------------------------------------------------------
    def _load_cache(self, filename):
        try:
            with open(os.path.join(self.plugin_dir, filename), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def _save_cache(self, filename, data):
        try:
            with open(os.path.join(self.plugin_dir, filename), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
        except OSError as exc:
            self._log(f"Could not save cache {filename}: {exc}", Qgis.Warning)

    def _wfs_layer(self, url, typename, label, srs=CRS_PL):
        uri = (f"pagingEnabled='default' preferCoordinatesForWfsT11='false' "
               f"restrictToRequestBBOX='1' srsname='{srs}' typename='{typename}' "
               f"url='{url}' version='auto'")
        layer = QgsVectorLayer(uri, label, "WFS")
        return layer if layer.isValid() else None

    def _list_feature_types(self, url):
        full = f"{url}?{urlencode({'service': 'WFS', 'request': 'GetCapabilities'})}"
        request = QgsBlockingNetworkRequest()
        if request.get(QNetworkRequest(QUrl(full))) != QgsBlockingNetworkRequest.NoError:
            self._log(f"GetCapabilities failed: {request.errorMessage()}", Qgis.Warning)
            return []
        try:
            root = ET.fromstring(bytes(request.reply().content()))
        except ET.ParseError as exc:
            self._log(f"GetCapabilities is not valid XML: {exc}", Qgis.Warning)
            return []
        names = []
        for el in root.iter():
            if el.tag.split("}")[-1] == "FeatureType":
                for child in el:
                    if child.tag.split("}")[-1] == "Name" and child.text:
                        names.append(child.text.strip())
        return names

    def _prg_typename(self, kind):
        """Type name of the PRG county / commune layer, discovered from GetCapabilities."""
        if kind in self._prg_typenames:
            return self._prg_typenames[kind]
        if not self._prg_feature_types:                 # one request serves both kinds
            self._prg_feature_types = self._list_feature_types(PRG_URL)
            self._log(f"PRG feature types: {self._prg_feature_types}")
        cfg = PRG_KINDS[kind]
        hits = sorted((n for n in self._prg_feature_types if cfg["keyword"] in n.lower()),
                      key=lambda n: "granic" not in n.lower())
        typename = hits[0] if hits else cfg["fallback"]
        self._prg_typenames[kind] = typename
        self._log(f"Using PRG {kind} layer: {typename}")
        return typename

    @staticmethod
    def _pick_field(layer, candidates):
        by_upper = {n.upper(): n for n in layer.fields().names()}
        for cand in candidates:                      # exact (case-insensitive)
            if cand.upper() in by_upper:
                return by_upper[cand.upper()]
        for cand in candidates:                      # partial match
            for upper, original in by_upper.items():
                if cand.upper() in upper:
                    return original
        return None

    def _prg_layer(self, kind):
        """Return (layer, code_field, name_field) for the PRG county/commune layer, or None."""
        cfg = PRG_KINDS[kind]
        typename = self._prg_typename(kind)
        layer = self._wfs_layer(PRG_URL, typename, cfg["layer_label"])
        if layer is None:
            self._warn(f"Nie udało się otworzyć warstwy {cfg['plural']} PRG ({typename}). "
                       "Szczegóły w Log Messages.")
            return None
        code_f = self._pick_field(layer, cfg["code_fields"])
        name_f = self._pick_field(layer, cfg["name_fields"])
        self._log(f"PRG {kind} fields: {layer.fields().names()} -> code={code_f}, name={name_f}")
        if not code_f or not name_f:
            self._warn(f"Nie rozpoznano pól kodu/nazwy {cfg['singular']}. "
                       f"Dostępne pola: {layer.fields().names()}")
            return None
        return layer, code_f, name_f

    def _fetch_units(self, kind, prefix):
        """Download (code, name) of all counties/communes whose TERYT code starts with `prefix`.

        Counties: prefix = 2-digit voivodeship code. Communes: prefix = 4-digit county code.
        Geometries are not requested, so this is quick.
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            found = self._prg_layer(kind)
            if found is None:
                return []
            layer, code_f, name_f = found

            # Server-side filter by TERYT prefix, so only the needed units are transferred.
            layer.setSubsetString(f"\"{code_f}\" LIKE '{prefix}%'")
            request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
            rows = {}
            for f in layer.getFeatures(request):
                code = str(f[code_f]).strip()
                if code.startswith(prefix):          # safety net if the filter was ignored
                    rows[code] = str(f[name_f]).strip()
            if not rows:
                self._warn(f"Brak {PRG_KINDS[kind]['plural']} dla kodu {prefix}. "
                           "Sprawdź Log Messages (pola warstwy PRG).")
                return []
            return sorted(rows.items(), key=lambda kv: (polish_sort_key(kv[1]), kv[0]))
        finally:
            QgsApplication.restoreOverrideCursor()

    def _fill_counties(self, *_args):
        box = self.dialog.countyBox
        # Block signals while filling, otherwise every change would start a commune download.
        box.blockSignals(True)
        try:
            box.clear()
            vcode = self.dialog.voivodeshipBox.currentData()
            counties = []
            if vcode is not None:
                counties = self._county_cache.get(vcode)
                if not counties:
                    counties = self._fetch_units("county", vcode)
                    if counties:
                        self._county_cache[vcode] = counties
                        self._save_cache(CACHE_FILE, self._county_cache)
            for code, name in counties or []:
                box.addItem(name, code)
        finally:
            box.blockSignals(False)
        self._fill_communes()

    def _fill_communes(self, *_args):
        box = self.dialog.communeBox
        box.clear()
        box.addItem(WHOLE_COUNTY, None)   # always available: use the whole county
        ccode = self.dialog.countyBox.currentData()
        if ccode is None:
            return

        communes = self._commune_cache.get(ccode)
        if not communes:
            communes = self._fetch_units("commune", ccode)
            if not communes:
                return                    # the "(cały powiat)" entry still works
            self._commune_cache[ccode] = communes
            self._save_cache(CACHE_FILE_COMMUNE, self._commune_cache)

        raw_names = {code: name for code, name in communes}
        for code, label in _label_communes([(c, n) for c, n in communes]):
            box.addItem(label, code)
            box.setItemData(box.count() - 1, raw_names[code], Qt.UserRole + 1)  # name without type suffix

    def _boundary_geometry(self, kind, code):
        """Boundary of one county/commune as a QgsGeometry in EPSG:2180 (or None)."""
        found = self._prg_layer(kind)
        if found is None:
            return None
        layer, code_f, _name_f = found
        layer.setSubsetString(f"\"{code_f}\" = '{code}'")
        geoms = [QgsGeometry(f.geometry()) for f in layer.getFeatures() if not f.geometry().isNull()]
        if not geoms:
            self._warn(f"Nie znaleziono granicy {PRG_KINDS[kind]['singular']} {code}.")
            return None
        geom = geoms[0] if len(geoms) == 1 else QgsGeometry.unaryUnion(geoms)
        return self._to_target_crs(layer, geom)

    @staticmethod
    def _to_target_crs(layer, geom):
        """Transform a geometry from the layer's CRS to EPSG:2180 (in place) and return it."""
        target = QgsCoordinateReferenceSystem(CRS_PL)
        if layer.crs().isValid() and layer.crs() != target:
            geom.transform(QgsCoordinateTransform(layer.crs(), target, QgsProject.instance().transformContext()))
        return geom

    def _prepared_communes(self, county_code):
        """All communes of a county with boundaries, ready for fast intersection tests.

        Returns a list of dicts {code, name, geom, engine}, or [] if they could not be loaded.
        """
        found = self._prg_layer("commune")
        if found is None:
            return []
        layer, code_f, name_f = found
        layer.setSubsetString(f"\"{code_f}\" LIKE '{county_code}%'")
        out = []
        for f in layer.getFeatures():
            code = str(f[code_f]).strip()
            if not code.startswith(county_code) or f.geometry().isNull():
                continue
            geom = self._to_target_crs(layer, QgsGeometry(f.geometry()))
            engine = QgsGeometry.createGeometryEngine(geom.constGet())
            engine.prepareGeometry()
            out.append({"code": code, "name": str(f[name_f]).strip(), "geom": geom, "engine": engine})
        self._log(f"Commune boundaries loaded for county {county_code}: {len(out)}")
        return out

    # ------------------------------------------------------------------
    # IAS download
    # ------------------------------------------------------------------
    def _download_geojson(self, typename, rect=None):
        """Download an IAS layer as GeoJSON. Returns (path, count).

        With a bbox it tries both possible axis orders and finally no bbox at all, because
        the server's handling of EPSG:2180 coordinates is not verified. Once a mode has produced
        objects it is remembered (also between sessions) and trusted, so an area without
        objects does not trigger a download of the whole layer.
        Returns (None, 0) if the request worked but returned no objects, (None, -1) on an error.
        """
        modes = ["xy", "yx", None] if rect is not None else [None]
        if rect is not None and self._bbox_mode in ("xy", "yx"):
            modes = [self._bbox_mode]

        for mode in modes:
            raw = self._request_ias(typename, rect, mode)
            if raw is None:
                return None, -1
            try:
                count = len(json.loads(raw).get("features", []))
            except (ValueError, AttributeError):
                self._warn("Serwer zwrócił nieprawidłowy JSON. Szczegóły w Log Messages.")
                return None, -1
            self._log(f"IAS request, bbox mode '{mode or 'none'}': {count} objects")
            if count > 0:
                if mode and mode != self._bbox_mode:
                    self._bbox_mode = mode
                    QgsSettings().setValue("IASParcelJoin/bboxMode", mode)
                path = os.path.join(tempfile.gettempdir(), f"ias_{typename.replace(':', '_')}.geojson")
                with open(path, "wb") as fh:
                    fh.write(raw)
                return path, count
        return None, 0

    def _request_ias(self, typename, rect=None, mode=None):
        """One GetFeature request. Returns the raw response bytes, or None on an error."""
        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typename": typename,
            "srsname": CRS_PL,
            "outputFormat": "application/json",
        }
        if rect is not None and mode == "xy":      # easting, northing
            params["bbox"] = (f"{rect.xMinimum()},{rect.yMinimum()},"
                              f"{rect.xMaximum()},{rect.yMaximum()},{CRS_PL}")
        elif rect is not None and mode == "yx":    # northing, easting, explicit URN
            params["bbox"] = (f"{rect.yMinimum()},{rect.xMinimum()},"
                              f"{rect.yMaximum()},{rect.xMaximum()},urn:ogc:def:crs:EPSG::2180")
        url = f"{WFS_URL}?{urlencode(params)}"
        self._log(f"GET {url}")

        # QgsBlockingNetworkRequest uses QGIS network settings (proxy, auth, timeout).
        request = QgsBlockingNetworkRequest()
        err = request.get(QNetworkRequest(QUrl(url)))
        if err != QgsBlockingNetworkRequest.NoError:
            self._warn(f"Nie udało się pobrać danych WFS: {request.errorMessage()}")
            return None

        raw = bytes(request.reply().content())
        self._log(f"Response head: {raw[:300]!r}")

        # GeoServer returns HTTP 200 with an XML ServiceException for a bad typename.
        if not raw.lstrip().startswith(b"{"):
            self._warn("Serwer nie zwrócił JSON-a (zła nazwa warstwy?). Szczegóły w Log Messages.")
            return None

        return raw

    def _fetch_ias_objects(self, typename, area_geom):
        """Download one IAS species layer and cut it to `area_geom` (EPSG:2180).

        Keeps only objects with all REQUIRED_FIELDS filled, with a point/polygon geometry that
        intersects the area. Returns a dict:
          status  "ok" | "empty" (server has no objects there) | "error" (reason already reported)
          fields  QgsFields of the IAS layer
          objects [(geometry as Multi*, 2D, EPSG:2180; attribute list; is_point), ...]
          total   objects downloaded; skipped / types: Counters for diagnostics
        """
        result = {"status": "error", "fields": None, "objects": [], "total": 0,
                  "skipped": Counter(), "types": Counter()}
        target_crs = QgsCoordinateReferenceSystem(CRS_PL)

        path, count = self._download_geojson(typename, area_geom.boundingBox() if USE_SERVER_BBOX else None)
        if not path:
            result["status"] = "empty" if count == 0 else "error"
            return result

        # Let OGR parse the GeoJSON: it handles Multi* types, Z values, nulls
        # and copies the real attribute names, so no field-guessing is needed.
        src = QgsVectorLayer(path, "ias_tmp", "ogr")
        try:
            if not src.isValid():
                self._warn("Nie udało się wczytać pobranego GeoJSON-a.")
                return result

            src_fields = src.fields()
            total = src.featureCount()
            self._log(f"Fields: {src_fields.names()}; downloaded objects: {total}")

            required = {}
            for name in REQUIRED_FIELDS:
                idx = src_fields.lookupField(name)
                if idx < 0:
                    self._warn(f"W danych brak wymaganego pola '{name}'. Dostępne pola: {src_fields.names()}")
                    return result
                required[name] = idx

            src_crs = src.crs() if src.crs().isValid() else target_crs
            xform = None
            if src_crs != target_crs:
                xform = QgsCoordinateTransform(src_crs, target_crs, QgsProject.instance().transformContext())

            engine = QgsGeometry.createGeometryEngine(area_geom.constGet())
            engine.prepareGeometry()

            skipped, types_seen, objects = Counter(), Counter(), []
            for f in src.getFeatures():
                # 1. completeness: every required field must have a value
                absent = [n for n, i in required.items() if _is_missing(f.attribute(i))]
                if absent:
                    skipped[f"brak {absent[0]}"] += 1
                    continue

                # 2. usable geometry
                g = f.geometry()
                if g is None or g.isNull():
                    skipped["brak geometrii"] += 1
                    continue
                wkb_name = QgsWkbTypes.displayString(g.wkbType())
                types_seen[wkb_name] += 1

                gtype = QgsWkbTypes.geometryType(g.wkbType())
                if gtype not in (QgsWkbTypes.PointGeometry, QgsWkbTypes.PolygonGeometry):
                    skipped[f"geometria {wkb_name}"] += 1
                    continue

                g = QgsGeometry(g)
                if xform is not None:
                    g.transform(xform)
                if QgsWkbTypes.hasZ(g.wkbType()):
                    g.get().dropZValue()
                if QgsWkbTypes.hasM(g.wkbType()):
                    g.get().dropMValue()
                g.convertToMultiType()  # Point -> MultiPoint, Polygon -> MultiPolygon

                # 3. exact test: the bbox download also returns objects next to the area
                if not engine.intersects(g.constGet()):
                    skipped["poza obszarem"] += 1
                    continue

                objects.append((g, f.attributes(), gtype == QgsWkbTypes.PointGeometry))

            result.update(status="ok", fields=src_fields, objects=objects, total=total,
                          skipped=skipped, types=types_seen)
            return result
        finally:
            del src
            try:
                os.remove(path)
            except OSError:
                pass

    def _make_memory_layer(self, geom_name, crs, label, fields):
        layer = QgsVectorLayer(f"{geom_name}?crs={crs.authid()}", label, "memory")
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()
        return layer

    def onDownloadIAS(self):
        d = self.dialog
        selected = d.speciesBox.currentText()
        number = d.speciesBox.currentData()
        county_code = d.countyBox.currentData()
        county_name = d.countyBox.currentText()
        commune_code = d.communeBox.currentData()        # None = whole county
        commune_name = (d.communeBox.currentData(Qt.UserRole + 1) or d.communeBox.currentText()) if commune_code else ""
        if number is None:
            self._warn("Nie wybrano gatunku.")
            return
        if county_code is None:
            self._warn("Nie wybrano powiatu (lista powiatów jest pusta, patrz Log Messages).")
            return

        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._download_and_load(selected, f"{WFS_PREFIX}:gatunek{number}",
                                    county_code, county_name, commune_code, commune_name)
        finally:
            QgsApplication.restoreOverrideCursor()

    def _download_and_load(self, selected, typename, county_code, county_name,
                           commune_code=None, commune_name=""):
        # The area to cut the data to: the commune if one is selected, otherwise the county.
        if commune_code:
            area_geom = self._boundary_geometry("commune", commune_code)
            area_name = f"{commune_name} ({county_name})"
        else:
            area_geom = self._boundary_geometry("county", county_code)
            area_name = county_name
        if area_geom is None:
            return
        target_crs = QgsCoordinateReferenceSystem(CRS_PL)

        res = self._fetch_ias_objects(typename, area_geom)
        if res["status"] == "empty":
            self.iface.messageBar().pushMessage(
                "Uwaga", f"{selected}: serwer nie zwrócił żadnych obiektów dla tego obszaru. "
                "Szczegóły w Log Messages.", level=Qgis.Warning)
        if res["status"] != "ok":
            return
        total, skipped, types_seen = res["total"], res["skipped"], res["types"]

        # IAS fields + the county / commune the object was matched to
        # (gmina_* stay empty when the whole county was selected)
        fields = res["fields"].toList() + [
            QgsField("powiat_nazwa", QVariant.String),
            QgsField("powiat_kod", QVariant.String),
            QgsField("gmina_nazwa", QVariant.String),
            QgsField("gmina_kod", QVariant.String),
            QgsField("gmina_inne", QVariant.String),   # other communes an object on a border also touches
        ]
        label = f"{selected} - {area_name}"
        pts = self._make_memory_layer("MultiPoint", target_crs, f"IAS punkty - {label}", fields)
        polys = self._make_memory_layer("MultiPolygon", target_crs, f"IAS poligony - {label}", fields)
        area_attrs = [county_name, county_code, commune_name or None, commune_code or None, None]

        # Whole county selected: work out the commune of every object from the commune boundaries.
        communes = []
        if not commune_code:
            communes = self._prepared_communes(county_code)
            if not communes:
                self._log("No commune boundaries available: the gmina_* fields stay empty.", Qgis.Warning)

        pt_feats, poly_feats = [], []
        crossing = 0   # objects lying on a commune border
        for g, attributes, is_point in res["objects"]:
            attrs = area_attrs
            if communes:
                best, others = _pick_communes(g, communes, is_point)
                if best is not None:
                    attrs = [county_name, county_code, best["name"], best["code"],
                             "; ".join(o["name"] for o in others) or None]
                    crossing += bool(others)

            layer, bucket = (pts, pt_feats) if is_point else (polys, poly_feats)
            nf = QgsFeature(layer.fields())
            nf.setGeometry(g)
            nf.setAttributes(attributes + attrs)
            bucket.append(nf)

        pts.dataProvider().addFeatures(pt_feats)
        polys.dataProvider().addFeatures(poly_feats)
        pts.updateExtents()
        polys.updateExtents()

        kept = len(pt_feats) + len(poly_feats)
        skipped_txt = ", ".join(f"{k}: {v}" for k, v in skipped.items())
        self._log(f"Geometry types seen: {dict(types_seen)}; kept {kept} of {total}; "
                  f"skipped: {dict(skipped)}; on a commune border: {crossing}")

        if not kept:
            reason = skipped_txt or "serwer zwrócił 0 obiektów dla tego obszaru"
            self.iface.messageBar().pushMessage(
                "Uwaga", f"{selected}, {area_name}: brak kompletnych obiektów ({reason}).",
                level=Qgis.Warning)
            return

        for layer in (pts, polys):
            if layer.featureCount() > 0:
                QgsProject.instance().addMapLayer(layer)

        border_txt = f"; na granicy gmin: {crossing}" if crossing else ""
        msg = (f"{area_name}: {len(pt_feats)} punktów, {len(poly_feats)} poligonów "
               f"(pobrano {total}" + (f"; pominięto - {skipped_txt}" if skipped_txt else "") + border_txt + ")")
        self.iface.messageBar().pushMessage("Sukces", msg, level=Qgis.Success)
        self._log(msg)

    # ------------------------------------------------------------------
    # Report: all listed species in one commune, with the parcels they lie on
    # ------------------------------------------------------------------
    def onReport(self):
        d = self.dialog
        commune_code = d.communeBox.currentData()
        if not commune_code:
            self._warn("Raport wymaga wybrania gminy (nie całego powiatu).")
            return
        species = [(d.speciesBox.itemData(i), d.speciesBox.itemText(i)) for i in range(d.speciesBox.count())]
        if not species:
            self._warn("Lista gatunków jest pusta (zmień Kategorię / Status).")
            return
        commune_name = d.communeBox.currentData(Qt.UserRole + 1) or d.communeBox.currentText()
        county_name = d.countyBox.currentText()

        settings = QgsSettings()
        start_dir = settings.value("IASParcelJoin/lastDir", os.path.expanduser("~"))
        default = os.path.join(start_dir, f"raport_IGO_{_safe_filename(commune_name)}_"
                                          f"{datetime.date.today().isoformat()}.xlsx")
        path, _filter = QFileDialog.getSaveFileName(d, "Zapisz raport", default,
                                                    "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".csv")):
            path += ".xlsx"
        settings.setValue("IASParcelJoin/lastDir", os.path.dirname(path))

        progress = QProgressDialog("Przygotowanie...", "Anuluj", 0, len(species), d)
        progress.setWindowTitle("Raport IGO")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        self._errors = []
        try:
            self._build_report(path, species, commune_code, commune_name, county_name, progress)
        except _Canceled:
            self.iface.messageBar().pushMessage("Raport", "Anulowano.", level=Qgis.Info)
        except OSError as exc:
            self._warn(f"Nie udało się zapisać pliku: {exc}")
        finally:
            errors, self._errors = self._errors, None
            progress.close()
            if errors:
                self.iface.messageBar().pushMessage(
                    "Uwaga", f"Podczas raportu wystąpiło błędów: {len(errors)} (pierwszy: {errors[0]}). "
                    "Szczegóły w Log Messages.", level=Qgis.Warning)

    @staticmethod
    def _check_canceled(progress):
        if progress.wasCanceled():
            raise _Canceled()

    def _build_report(self, path, species, commune_code, commune_name, county_name, progress):
        area_geom = self._boundary_geometry("commune", commune_code)
        if area_geom is None:
            return

        # Phase 1: IAS objects of every listed species inside the commune
        objects, notes = [], {}
        for i, (number, label) in enumerate(species):
            self._check_canceled(progress)
            progress.setLabelText(f"Gatunek {i + 1}/{len(species)}: {label}")
            progress.setValue(i)
            QgsApplication.processEvents()

            res = self._fetch_ias_objects(f"{WFS_PREFIX}:gatunek{number}", area_geom)
            if res["status"] == "error":
                notes[number] = "błąd pobierania"
                continue
            if res["status"] == "ok":
                cols = _ias_columns(res["fields"].names())
                for g, attributes, is_point in res["objects"]:
                    obj = {"number": number, "geom": g, "is_point": is_point}
                    for key, idx in cols.items():
                        obj[key] = _plain(attributes[idx]) if idx is not None else ""
                    objects.append(obj)
                if res["skipped"]:
                    self._log(f"{label}: skipped {dict(res['skipped'])}")
        progress.setValue(len(species))
        self._check_canceled(progress)

        # Phase 2: parcels (EGiB) under those objects
        index, parcels = None, None
        if objects:
            collected = self._collect_parcels(objects, commune_code, progress, self.dialog.parcelLayerBox.currentData())
            if collected is None:
                notes["_parcels"] = "nie pobrano działek"
            else:
                index, parcels = collected

        rows, summary, parcel_rows = self._assemble_report(species, objects, index, parcels,
                                              commune_name, county_name, notes)
        self._write_report(path, rows, summary, parcel_rows, commune_name, county_name, parcels is not None)

        n_parcels = len({r[12] for r in rows if r[12]})
        msg = (f"Raport zapisany: {path} ({len(objects)} obiektów, {n_parcels} działek, "
               f"{len(rows)} wierszy)")
        if parcels is None and objects:
            msg += ". UWAGA: nie pobrano działek z EGiB"
        self.iface.messageBar().pushMessage("Sukces", msg, level=Qgis.Success)
        self._log(msg)

    def _open_parcel_layer(self, layer_id=None):
        """(layer, {logical name: field name or None}) for the parcels, or None.

        With `layer_id`, a parcel layer of the project is used instead of the EGiB service."""
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer is None or not layer.isValid():
                self._warn("Wybrana warstwa działek nie jest już dostępna w projekcie.")
                return None
            cols = {key: self._pick_field(layer, cands + (CUSTOM_ID_FIELDS if key == "id" else ()))
                    for key, cands in PARCEL_FIELDS.items()}
            self._log(f"Using project parcel layer '{layer.name()}': {layer.fields().names()} -> {cols}; "
                      f"CRS {layer.crs().authid()}")
            return layer, cols
        layer = self._wfs_layer(EGIB_URL, EGIB_TYPENAME, "dzialki")
        if layer is None:
            self._warn("Nie udało się otworzyć usługi działek EGiB. Szczegóły w Log Messages.")
            return None
        cols = {key: self._pick_field(layer, cands) for key, cands in PARCEL_FIELDS.items()}
        self._log(f"EGiB fields: {layer.fields().names()} -> {cols}; CRS {layer.crs().authid()}")
        if not cols["id"]:
            self._warn(f"Nie rozpoznano pola ID działki. Dostępne pola: {layer.fields().names()}")
            return None
        return layer, cols

    def _collect_parcels(self, objects, commune_code, progress, layer_id=None):
        """Download the parcels under all objects. Returns (spatial index, {id: parcel}) or None."""
        opened = self._open_parcel_layer(layer_id)
        if opened is None:
            return None
        layer, cols = opened
        target = QgsCoordinateReferenceSystem(CRS_PL)
        to_layer = None
        if layer.crs().isValid() and layer.crs() != target:
            to_layer = QgsCoordinateTransform(target, layer.crs(), QgsProject.instance().transformContext())

        # Grid cells to request: those touched by an object (for polygons: by the real shape)
        cells = set()
        for o in objects:
            g, box = o["geom"], o["geom"].boundingBox()
            cand = _grid_cells(box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum(), PARCEL_CELL_M)
            if len(cand) > 1 and not o["is_point"]:
                cand = [c for c in cand if QgsGeometry.fromRect(_cell_rect(c)).intersects(g)]
            cells.update(cand)
        cells = sorted(cells)
        self._log(f"Parcel requests: {len(cells)} cell(s) of {PARCEL_CELL_M} m for {len(objects)} objects")

        # Parcel IDs start with the TERYT code of the commune. Look at one real parcel to learn the
        # exact format, then let the server skip all other communes. No sample -> no filter.
        if layer_id:   # the person's own layer: use it as it is, no ID filter
            return self._download_parcels(layer, cols, cells, to_layer, progress)
        prefix = self._probe_id_prefix(layer, cols, objects, commune_code, to_layer)
        if prefix:
            layer.setSubsetString(f"\"{cols['id']}\" LIKE '{prefix}%'")
            result = self._download_parcels(layer, cols, cells, to_layer, progress)
            if result[1]:
                self._log(f"Parcels downloaded with ID filter '{prefix}%': {len(result[1])}")
                return result
            self._log("ID filter returned no parcels; repeating without the filter", Qgis.Warning)
            layer.setSubsetString("")
        return self._download_parcels(layer, cols, cells, to_layer, progress)

    def _probe_id_prefix(self, layer, cols, objects, commune_code, to_layer):
        """Commune part of the parcel ID as EGiB really writes it, e.g. '161101_3' (or '')."""
        g = objects[0]["geom"].centroid() if not objects[0]["is_point"] else objects[0]["geom"]
        if g is None or g.isNull():
            return ""
        p = g.asPoint()
        rect = QgsRectangle(p.x() - 5, p.y() - 5, p.x() + 5, p.y() + 5)
        if to_layer is not None:
            rect = to_layer.transformBoundingBox(rect)
        for f in layer.getFeatures(QgsFeatureRequest().setFilterRect(rect).setLimit(1)):
            sample = str(f[cols["id"]]).strip()
            self._log(f"Sample parcel ID: {sample!r} (commune {commune_code})")
            head = sample.split(".")[0]
            return head if head.startswith(commune_code[:6]) else ""
        return ""

    def _download_parcels(self, layer, cols, cells, to_layer, progress):
        progress.setMaximum(len(cells))
        progress.setValue(0)
        index, parcels, seen = QgsSpatialIndex(), {}, set()
        for n, cell in enumerate(cells):
            self._check_canceled(progress)
            progress.setLabelText(f"Działki (EGiB): {n + 1}/{len(cells)}")
            progress.setValue(n)
            QgsApplication.processEvents()

            rect = _cell_rect(cell)
            if to_layer is not None:
                rect = to_layer.transformBoundingBox(rect)
            for f in layer.getFeatures(QgsFeatureRequest().setFilterRect(rect)):
                if f.geometry() is None or f.geometry().isNull():
                    continue
                raw_id = f[cols["id"]] if cols["id"] else None
                pid = f"fid{f.id()}" if _is_missing(raw_id) else str(raw_id).strip()
                if pid in seen:
                    continue
                seen.add(pid)
                geom = self._to_target_crs(layer, QgsGeometry(f.geometry()))
                key = len(parcels)
                feat = QgsFeature(key)
                feat.setGeometry(geom)
                index.addFeature(feat)
                parcel = {"id": pid, "geom": geom}
                for name, field in cols.items():
                    if name != "id":
                        parcel[name] = _plain(f[field]) if field else ""
                parcels[key] = parcel
        progress.setValue(len(cells))
        self._log(f"Parcels downloaded: {len(parcels)}")
        return index, parcels

    @staticmethod
    def _assemble_report(species, objects, index, parcels, commune_name, county_name, notes):
        """Build the report rows (one per object x parcel) and the per-species summary rows."""
        order = {number: i for i, (number, _label) in enumerate(species)}
        objects = sorted(objects, key=lambda o: (order[o["number"]], str(o["nrrej"])))

        stats = {number: {"objects": 0, "parcels": set(), "no_parcel": 0} for number, _l in species}
        rows, used_parcels = [], {}
        for o in objects:
            _n, polish, latin, _inv, _spr, _cat = SPECIES_BY_NUMBER[o["number"]]
            name = polish or latin
            base = [commune_name, county_name, name, latin, IGO_LIST.get(o["number"], ""),
                    STATUS_NAMES.get(STATUS.get(o["number"]), ""),
                    o["nrrej"], "punkt" if o["is_point"] else "poligon",
                    o["min"], o["max"], o["unit"], o["date"]]
            matches = _match_parcels(o["geom"], o["is_point"], index, parcels) if parcels is not None else []
            wkt = _wkt(o["geom"])
            st = stats[o["number"]]
            st["objects"] += 1
            if matches:
                for parcel, area in matches:
                    st["parcels"].add(parcel["id"])
                    rows.append(base + [parcel["id"], parcel["number"], parcel["precinct"],
                                        parcel["precinct_no"], parcel["commune"], parcel["area"],
                                        round(area, 2) if area is not None else "", wkt])
                    used_parcels.setdefault(parcel["id"], parcel)
            else:
                st["no_parcel"] += 1
                rows.append(base + [""] * 7 + [wkt])

        summary = []
        for number, label in species:
            _n, polish, latin, _inv, _spr, _cat = SPECIES_BY_NUMBER[number]
            st = stats[number]
            note = notes.get(number) or ("brak stwierdzeń w gminie" if not st["objects"] else "")
            summary.append([polish or latin, latin, IGO_LIST.get(number, ""),
                            STATUS_NAMES.get(STATUS.get(number), ""),
                            st["objects"], len(st["parcels"]), st["no_parcel"], note])
        parcel_rows = [[p["id"], p["number"], p["precinct"], p["precinct_no"], p["commune"], _wkt(p["geom"])]
                       for p in sorted(used_parcels.values(), key=lambda p: str(p["id"]))]
        return rows, summary, parcel_rows

    @staticmethod
    def _write_report(path, rows, summary, parcel_rows, commune_name, county_name, parcels_ok):
        if write_xlsx is None and not path.lower().endswith(".csv"):
            path = os.path.splitext(path)[0] + ".csv"  # xlsx_writer.py missing -> CSV
        if path.lower().endswith(".csv"):
            # ';' separator and decimal comma: opens correctly in Polish Excel
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh, delimiter=";")
                writer.writerow(REPORT_HEADER)
                for row in rows:
                    writer.writerow([str(v).replace(".", ",") if isinstance(v, float) else v for v in row])
            return

        info = [
            ["Raport inwazyjnych gatunków obcych", ""],
            ["Gmina", commune_name],
            ["Powiat", county_name],
            ["Data wygenerowania", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Źródło obiektów", "GDOŚ, system Inwazyjne gatunki obce (inwazyjne.gdos.gov.pl)"],
            ["Źródło granic", "Państwowy Rejestr Granic (GUGiK)"],
            ["Źródło działek", "EGiB, usługa zbiorcza WFS (GUGiK) lub warstwa z projektu" if parcels_ok else "NIE POBRANO"],
            ["Uwaga 1", "Pominięto obiekty bez numeru rejestracyjnego (nrrej) lub bez geometrii."],
            ["Uwaga 2", "Obiekt leżący na kilku działkach ma osobny wiersz dla każdej działki; "
                        "dla poligonów podano powierzchnię w działce."],
            ["Uwaga 4", "WKT w układzie EPSG:2180 (metry). Arkusz 'WKT działek' zawiera geometrie działek z raportu; "
                        "zbyt długie WKT (limit komórki Excela) są uproszczone."],
            ["Uwaga 3", "Lista (UE/PL) i status (szybka eliminacja / rozprzestrzenione) pochodzą z danych wtyczki."],
        ]
        write_xlsx(path, [
            {"name": "Raport", "header": REPORT_HEADER, "rows": rows},
            {"name": "Podsumowanie", "header": SUMMARY_HEADER, "rows": summary},
            {"name": "WKT działek", "header": PARCEL_WKT_HEADER, "rows": parcel_rows},
            {"name": "Informacje", "header": None, "rows": info, "widths": [24, 90]},
        ])
