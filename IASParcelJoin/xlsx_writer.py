# -*- coding: utf-8 -*-
"""Minimal .xlsx writer without third-party packages (QGIS' Python often has no openpyxl).

Supports several sheets, a bold header row (frozen, with filter), text / number cells and
automatic column widths. That is all the report needs.
"""
import math
import re
import zipfile
from xml.sax.saxutils import escape

_ILLEGAL_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_BAD_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")


def _col_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA ..."""
    letters, n = "", index + 1
    while n:
        n, rest = divmod(n - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _cell_xml(ref, value, style):
    s = f' s="{style}"' if style else ""
    if value is None or value == "":
        return f'<c r="{ref}"{s}/>' if style else ""
    if isinstance(value, bool):
        return f'<c r="{ref}"{s} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return ""
        return f'<c r="{ref}"{s}><v>{repr(value)}</v></c>'
    text = _ILLEGAL_XML.sub("", str(value))
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'


def _sheet_xml(header, rows, widths):
    n_cols = max([len(header or [])] + [len(r) for r in rows] + [1])
    cols = "".join(
        f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)
    )
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if header:
        out.append('<sheetViews><sheetView workbookViewId="0">'
                   '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                   '</sheetView></sheetViews>')
    if cols:
        out.append(f"<cols>{cols}</cols>")
    out.append("<sheetData>")
    row_no = 0
    all_rows = ([header] if header else []) + list(rows)
    for r_index, row in enumerate(all_rows):
        row_no += 1
        style = 1 if (header and r_index == 0) else 0
        cells = "".join(_cell_xml(f"{_col_letter(c)}{row_no}", v, style) for c, v in enumerate(row))
        out.append(f'<row r="{row_no}">{cells}</row>')
    out.append("</sheetData>")
    if header:
        out.append(f'<autoFilter ref="A1:{_col_letter(n_cols - 1)}{max(row_no, 1)}"/>')
    out.append("</worksheet>")
    return "".join(out)


def _auto_widths(header, rows):
    n_cols = max([len(header or [])] + [len(r) for r in rows[:300]] + [0])
    widths = []
    for c in range(n_cols):
        longest = len(str(header[c])) if header and c < len(header) else 0
        for row in rows[:300]:
            if c < len(row) and row[c] is not None:
                longest = max(longest, len(str(row[c])))
        widths.append(min(max(longest + 2, 8), 60))
    return widths


def _safe_sheet_name(name, used):
    name = _BAD_SHEET_CHARS.sub(" ", name).strip()[:31] or "Arkusz"
    base, i = name, 2
    while name.lower() in used:
        name = f"{base[:28]} {i}"
        i += 1
    used.add(name.lower())
    return name


def write_xlsx(path, sheets):
    """Write `sheets` to `path`.

    `sheets` is a list of dicts: {"name": str, "header": [..] or None, "rows": [[..], ..]}.
    """
    used = set()
    names = [_safe_sheet_name(s["name"], used) for s in sheets]

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(sheets)))
        + "</Types>")
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>")
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(f'<sheet name="{escape(n, {chr(34): "&quot;"})}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
                  for i, n in enumerate(names))
        + "</sheets></workbook>")
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(sheets)))
        + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>")
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="3"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFD9E2EC"/><bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", styles)
        for i, sheet in enumerate(sheets):
            header, rows = sheet.get("header"), sheet.get("rows", [])
            widths = sheet.get("widths") or _auto_widths(header, rows)
            zf.writestr(f"xl/worksheets/sheet{i + 1}.xml", _sheet_xml(header, rows, widths))
