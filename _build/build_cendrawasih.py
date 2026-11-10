#!/usr/bin/env python3
"""Rebuild gamelan/cendrawasih/index.html from the spreadsheet.

    python3 _build/build_cendrawasih.py <Cendrawasih.xlsx>

Replaces only the notation. Prose, layout, player and controls are left as
they are, and the timing comes from _build/timing_cendrawasih.json.

Cendrawasih differs from Pendet: bars are numbered within each section, three
sections are played three times, and the timing is a set of measured anchors
with a piecewise-linear map between them rather than a time per block. So a
section changing length moves the knots, which is a judgement call - the build
stops rather than guessing.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PAGE = os.path.join(REPO, 'gamelan', 'cendrawasih', 'index.html')
TIMING = os.path.join(HERE, 'timing_cendrawasih.json')

ROWS = ['Jegog', 'Calung', 'Kendang Wadon', 'Pemade Polos', 'Pemade Sangsih',
        'Sangsih Reyong (4)', 'Polos Reyong (3)', 'Sangsih Reyong (2)',
        'Polos Reyong (1)', 'Kajar', 'Gong/Kempur/Tong']
# the kendang line appears only in the bars that carry it
OPTIONAL = {'Kendang Wadon'}
LABELS = set(ROWS)

problems, strays = [], []
def fail(m): problems.append(m)


def norm(v):
    """'B section (Pengawak) - 3x' -> 'B section (Pengawak)'"""
    return re.sub(r'\s*[-\u2013]\s*\d+\s*[xX]\s*$', '', v).strip()


def parse(path, secnames):
    """Blocks are runs of instrument rows. There is no bar-number row in this
    sheet, and the 'beat' label above a block is sometimes missing, so neither
    is used to find anything."""
    cells, nrows, ncols = sheet.read(path)
    get = lambda r, c: cells.get((r, c), {}).get('v', '')
    data_in = lambda r: sum(1 for c in range(2, 34) if get(r, c))

    blocks, sec, si = [], None, 0
    r = 1
    while r <= nrows:
        v = get(r, 1)
        if v and v not in LABELS and v != 'beat':
            n = norm(v)
            if si < len(secnames) and (secnames[si] == n or secnames[si].startswith(n + ' ')):
                sec, si = secnames[si], si + 1
            elif n in secnames:
                sec = n
            r += 1
            continue
        if v not in LABELS:
            r += 1
            continue

        # a block: consecutive rows that are labelled parts, plus any unlabelled
        # row carrying data between them (which is an error, reported below)
        found, unlabelled, rr = {}, [], r
        while rr <= nrows:
            lv = get(rr, 1)
            if lv in LABELS:
                found[lv] = rr
            elif lv == '' and data_in(rr):
                unlabelled.append(rr)
            else:
                break
            rr += 1

        beat = r - 1
        # how wide is this block? take the rightmost column holding anything,
        # across the beat row and every part, ignoring the helper column at 35.
        right = 1
        for x in list(found.values()) + [beat]:
            for c in range(2, 34):
                if get(x, c):
                    right = max(right, c)
        width = -(-(right - 1) // 16) * 16        # round up to whole bars
        last_label = max(found.values(), default=0)
        for u in unlabelled:
            if u > last_label:
                # trailing stray below the last part: note it, carry on
                strays.append((u, data_in(u)))
                continue
            before = [l for l in ROWS if l in found and found[l] < u]
            guess = ROWS[ROWS.index(before[-1]) + 1] if before and ROWS.index(before[-1]) + 1 < len(ROWS) else None
            fail(f'sheet row {u}: this row has {data_in(u)} cells of notation but '
                 f'nothing in column A, so the part it belongs to is unknown and '
                 f'it would be dropped.'
                 + (f" By its position it should be labelled {guess!r} - type that "
                    f"into column A of sheet row {u}." if guess else ''))
        missing = [a for a in ROWS if a not in found and a not in OPTIONAL]
        if missing and not unlabelled:
            fail(f'sheet row {r} (section {sec!r}): no row labelled '
                 + ', '.join(repr(m) for m in missing))
        if sec is None:
            fail(f'sheet row {r}: a block before any section heading')

        blocks.append({'sec': sec, 'nbar': max(1, width // 16),
                       'rows': found, 'row': r, 'beat': beat})
        r = rr

    # flatten to one entry per notated bar, in order
    bars = []
    for b in blocks:
        for i in range(b['nbar']):
            bcells = {}          # not 'cells': that name is the sheet itself
            for lab in ROWS:
                rr = b['rows'].get(lab)
                if rr is not None:
                    bcells[lab] = [get(rr, 2 + i * 16 + k) for k in range(16)]
            bars.append({'sec': b['sec'], 'cells': bcells})
    return blocks, bars


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    if not os.path.exists(src):
        sys.exit(f'no such file: {src}')

    T = json.load(open(TIMING))
    secnames = [s['name'] for s in T['sections']]

    print(f'reading {src}')
    blocks, bars = parse(src, secnames)

    # section bar counts, in the order they appear
    seen, counts = [], {}
    for b in bars:
        if not seen or seen[-1] != b['sec']:
            seen.append(b['sec'])
        counts[b['sec']] = counts.get(b['sec'], 0) + 1
    print(f'  {len(blocks)} blocks in the sheet, {len(bars)} notated bars')
    for s in seen:
        print(f'    {s:28s} {counts[s]:>3} bars')
    kend = sum(1 for b in bars if 'Kendang Wadon' in b['cells'])
    print(f'  bars carrying a kendang line: {kend}')
    for u, n in strays:
        print(f'  sheet row {u}: {n} cells below the last part, unlabelled - ignored')

    if seen != secnames:
        fail('the sections in the sheet are not the ones in the timing file.\n'
             f'      sheet:  {seen}\n      timing: {secnames}')
    else:
        for s in T['sections']:
            if counts.get(s['name']) != s['bars']:
                fail(f"section {s['name']!r} has {counts.get(s['name'])} bars, the "
                     f"timing file expects {s['bars']}. A section changing length "
                     f"moves the anchors, which has to be re-measured against the "
                     f"recording - this build will not guess. Ask Claude.")

    if problems:
        print('\nSTOPPED. Nothing was written.\n')
        for p in problems:
            print('  * ' + p)
        print()
        sys.exit(1)

    # played-bar index where each section starts
    start, k = {}, 0
    for s in T['sections']:
        start[s['name']] = k
        k += s['bars'] * s['rep']
    NB = k
    knots = T['knots']
    if knots[-1][1] != NB:
        fail(f"the last timing knot is at bar {knots[-1][1]} but the piece is now "
             f"{NB} played bars long. The knots need re-measuring. Ask Claude.")
    for a, b2 in zip(knots, knots[1:]):
        if b2[1] <= a[1]:
            fail(f"timing knots {a[0]!r} and {b2[0]!r} are out of order "
                 f"(bars {a[1]} then {b2[1]}).")

    if problems:
        print('\nSTOPPED. Nothing was written.\n')
        for p2 in problems:
            print('  * ' + p2)
        print()
        sys.exit(1)

    page = open(PAGE, encoding='utf-8').read()
    m = re.search(r'^const D = (\{.*\});$', page, re.M)
    if not m:
        sys.exit(f'could not find the data line in {PAGE}')
    D = json.loads(m.group(1))

    changed, diffs = 0, []
    out = []
    for name in secnames:
        idx = [i for i, b in enumerate(bars) if b['sec'] == name]
        for j in range(0, len(idx), 2):          # the page pairs bars by index
            grp = idx[j:j + 2]
            cells = {}
            for lab in ROWS:
                if not any(lab in bars[g]['cells'] for g in grp):
                    continue
                seq = []
                for g in grp:
                    seq += bars[g]['cells'].get(lab, [''] * 16)
                cells[lab] = seq
            out.append({'sec': name, 'n': [g - idx[0] for g in grp],
                        'label': [g - idx[0] + 1 for g in grp],
                        'nbar': len(grp), 'cells': cells})

    for new, old in zip(out, D['blocks']):
        for lab, seq in new['cells'].items():
            o = old['cells'].get(lab, [])
            for i, (a, b2) in enumerate(zip(seq, o)):
                if a != b2:
                    changed += 1
                    diffs.append((new['sec'], new['label'][i // 16], i % 16 / 4 + 1, lab, b2, a))
            changed += abs(len(seq) - len(o))
        for lab in old['cells']:
            if lab not in new['cells']:
                changed += len(old['cells'][lab])

    D['blocks'] = out
    D['order'] = secnames
    D['rep'] = {s['name']: s['rep'] for s in T['sections']}
    D['nb'] = {s['name']: s['bars'] for s in T['sections']}
    D['start'], D['NB'], D['knots'] = start, NB, knots
    D['DUR'] = T['DUR']
    for k2 in ('anch', 'rB', 'knotbars'):
        D.pop(k2, None)

    new_page = page[:m.start()] + 'const D = ' + json.dumps(D, separators=(',', ':')) + ';' + page[m.end():]
    if new_page == page:
        print('\nNo change - the page already matches the sheet.')
        sys.exit(3)
    open(PAGE, 'w', encoding='utf-8').write(new_page)
    print(f'\nwrote {os.path.relpath(PAGE, REPO)}  -  {changed} cells differ\n')
    if diffs:
        from collections import Counter
        print('  by part: ' + ', '.join(f'{k2} {v}' for k2, v in Counter(d[3] for d in diffs).most_common()))
        print('  by section: ' + ', '.join(f'{k2} {v}' for k2, v in Counter(d[0] for d in diffs).most_common()))
        print()
        print(f'  {"section":26} {"bar":>4} {"beat":>5}  {"part":<20} {"was":>6} -> now')
        for d in sorted(diffs, key=lambda d: (secnames.index(d[0]), d[1], d[2], d[3]))[:40]:
            print(f'  {d[0][:26]:26} {d[1]:>4} {d[2]:>5.2f}  {d[3]:<20} {d[4]!r:>6} -> {d[5]!r}')
        if len(diffs) > 40:
            print(f'  ... and {len(diffs) - 40} more')
    print('\nOpen the page to check it, then:  ./deploy.sh "what you changed"')


if __name__ == '__main__':
    main()
