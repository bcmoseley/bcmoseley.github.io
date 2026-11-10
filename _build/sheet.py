"""Read an .xlsx with the standard library only.

Returns each cell's displayed text and whether it is italic, which is how the
sheet marks a muted strike. No third-party packages, so this runs on any
Python 3 without installing anything.
"""
import zipfile, re
from xml.etree import ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


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

        # style index -> italic
        italic = {}
        if 'xl/styles.xml' in z.namelist():
            st = ET.fromstring(z.read('xl/styles.xml'))
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
                # numbers come through as '82' or '82.0'
                if t in (None, 'n'):
                    try:
                        f = float(v)
                        v = str(int(f)) if f == int(f) else str(f)
                    except ValueError:
                        pass
                i, sz = italic.get(int(c.get('s', 0)), (False, None))
                cells[(r, col)] = {'v': str(v).strip(), 'i': i, 'sz': sz}
        return cells, nrows, ncols
