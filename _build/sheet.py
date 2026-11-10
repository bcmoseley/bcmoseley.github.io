"""Read an .xlsx with the standard library only.

Returns each cell's displayed text and whether it is italic, which is how the
sheet marks a muted strike. No third-party packages, so this runs on any
Python 3 without installing anything.
"""
import zipfile, re, datetime
from xml.etree import ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# Spreadsheets quietly turn things like "1/3" into a date. The gamelan sheets
# use that spelling for a byar pair, so a cell formatted as a date has to be
# rendered back the way the sheet displays it, not left as the serial number.
BUILTIN_DATE = set(range(14, 23)) | set(range(45, 48))
_EPOCH = datetime.datetime(1899, 12, 30)


def _is_date_fmt(code, fmt_id):
    if fmt_id in BUILTIN_DATE:
        return True
    if not code:
        return False
    bare = re.sub(r'\[[^\]]*\]|"[^"]*"|\\.', '', code)
    return bool(re.search(r'[ymdhs]', bare, re.I))


def _render_date(serial, code):
    """Render an Excel date serial using the sheet's own format code."""
    try:
        dt = _EPOCH + datetime.timedelta(days=float(serial))
    except (ValueError, OverflowError):
        return str(serial)
    code = re.sub(r'\[[^\]]*\]', '', code or 'm/d')
    out, i = [], 0
    while i < len(code):
        m = re.match(r'(y{1,4}|m{1,4}|d{1,4}|h{1,2}|s{1,2})', code[i:], re.I)
        if m:
            tok = m.group(0).lower()
            n = len(tok)
            if tok[0] == 'y':
                out.append(f'{dt.year:04d}' if n > 2 else f'{dt.year % 100:02d}')
            elif tok[0] == 'm':
                out.append(f'{dt.month:02d}' if n >= 2 else str(dt.month))
            elif tok[0] == 'd':
                out.append(f'{dt.day:02d}' if n >= 2 else str(dt.day))
            elif tok[0] == 'h':
                out.append(f'{dt.hour:02d}' if n >= 2 else str(dt.hour))
            else:
                out.append(f'{dt.minute:02d}')
            i += n
        else:
            if code[i] not in '\\"':
                out.append(code[i])
            i += 1
    return ''.join(out)


def _text(el):
    """All text under <si>, honouring rich-text runs."""
    return ''.join(t.text or '' for t in el.iter(NS + 't'))


def _colnum(ref):
    """'BC12' -> 55"""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n


def read(path, sheet_index=0):
    """-> (cells, nrows, ncols)

    cells maps (row, col) 1-based to {'v': displayed text, 'i': italic bool}.
    """
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared = [_text(si) for si in root.findall(NS + 'si')]

        # numFmtId -> format code (custom overrides builtin)
        codes = {}
        # style index -> (italic, size), and style index -> format code
        italic, numfmt = {}, {}
        if 'xl/styles.xml' in z.namelist():
            st = ET.fromstring(z.read('xl/styles.xml'))
            for n in st.iter(NS + 'numFmt'):
                codes[int(n.get('numFmtId'))] = n.get('formatCode')
            fonts = []
            fel = st.find(NS + 'fonts')
            if fel is not None:
                for f in fel.findall(NS + 'font'):
                    i = f.find(NS + 'i') is not None
                    szel = f.find(NS + 'sz')
                    sz = float(szel.get('val')) if szel is not None else None
                    fonts.append((i, sz))
            xfs = st.find(NS + 'cellXfs')
            if xfs is not None:
                for k, xf in enumerate(xfs.findall(NS + 'xf')):
                    fid = int(xf.get('fontId', 0))
                    italic[k] = fonts[fid] if fid < len(fonts) else (False, None)
                    nid = int(xf.get('numFmtId', 0))
                    numfmt[k] = (nid, codes.get(nid))

        names = sorted(n for n in z.namelist()
                       if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
        ws = ET.fromstring(z.read(names[sheet_index]))

        cells, nrows, ncols = {}, 0, 0
        for row in ws.iter(NS + 'row'):
            r = int(row.get('r'))
            nrows = max(nrows, r)
            for c in row.findall(NS + 'c'):
                ref = c.get('r') or ''
                col = _colnum(ref)
                ncols = max(ncols, col)
                t = c.get('t')
                if t == 'inlineStr':
                    isel = c.find(NS + 'is')
                    v = _text(isel) if isel is not None else ''
                else:
                    vel = c.find(NS + 'v')
                    v = vel.text if vel is not None and vel.text is not None else ''
                    if t == 's' and v != '':
                        v = shared[int(v)]
                if v == '':
                    continue
                sidx = int(c.get('s', 0))
                # numbers come through as '82' or '82.0'; a date-formatted cell
                # is a serial that has to be rendered the way the sheet shows it
                if t in (None, 'n'):
                    fid, code = numfmt.get(sidx, (0, None))
                    if _is_date_fmt(code, fid):
                        v = _render_date(v, code)
                    else:
                        try:
                            f = float(v)
                            v = str(int(f)) if f == int(f) else str(f)
                        except ValueError:
                            pass
                i, sz = italic.get(sidx, (False, None))
                cells[(r, col)] = {'v': str(v).strip(), 'i': i, 'sz': sz}
        return cells, nrows, ncols
