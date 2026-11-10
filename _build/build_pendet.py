#!/usr/bin/env python3
"""Rebuild gamelan/pendet/index.html from the spreadsheet.

    python3 _build/build_pendet.py <Pendet.xlsx>

Replaces only the notation. Everything else in the page - the prose, the
layout, the player, the parts panel - is left exactly as it is, and the
timing comes from _build/timing_pendet.json, never from the sheet.

Nothing is written unless every check passes. The checks exist because each
one has caught a real mistake:

  * a block's label cell holding a note instead of 'bar'   (m92-93 vanished)
  * a deleted row label                                    (a part vanished)
  * the sheet's block grouping changing                    (timing silently wrong)
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PAGE = os.path.join(REPO, 'gamelan', 'pendet', 'index.html')
TIMING = os.path.join(HERE, 'timing_pendet.json')

# the instrument rows, in the order the page shows them. The sheet's column A
# uses these same names.
ROWS = ['Jegog', 'Calung', 'Pemade Polos', 'Pemade Sangsih',
        'Sangsih Reyong (4)', 'Polos Reyong (3)',
        'Sangsih Reyong (2)', 'Polos Reyong (1)',
        'Kajar', 'Gong/Kempur/Tong']
SHEET_LABELS = set(ROWS)

problems, notes = [], []


def fail(msg):
    problems.append(msg)


def parse(path):
    cells, nrows, ncols = sheet.read(path)
    get = lambda r, c: cells.get((r, c), {}).get('v', '')
    ital = lambda r, c: cells.get((r, c), {}).get('i', False)
    size = lambda r, c: cells.get((r, c), {}).get('sz', None)

    blocks = []          # [{'row':, 'bars':[(n,col,len)], 'rows':{label:row}}]
    for r in range(1, nrows):
        # a block is identified by its beat row, NOT by the word 'bar' above it:
        # that cell sometimes holds an annotation instead.
        if get(r + 1, 1) != 'beat':
            continue
        nums = []
        for c in range(2, ncols + 1):
            v = get(r, c)
            if re.fullmatch(r'\d+', v):
                nums.append((c, int(v)))
        if not nums:
            continue
        tag = get(r, 1)
        if tag != 'bar':
            notes.append((r, [n for _, n in nums], tag))
        # count only the beat numbers: the sheet has a trailing helper column
        # ('common', 'reyong', ...) that is not part of the grid.
        width = sum(1 for c in range(2, ncols + 1)
                    if re.fullmatch(r'\d+', get(r + 1, c)))
        end = 2 + width
        bars = []
        for i, (c, n) in enumerate(nums):
            nxt = nums[i + 1][0] if i + 1 < len(nums) else end
            span = nxt - c
            if span % 4:
                fail(f'sheet row {r}: bar {n} spans {span} columns, not a multiple of 4')
            bars.append((n, c, span // 4))
        found = {}
        rr = r + 2
        while rr <= nrows and get(rr, 1) in SHEET_LABELS:
            found[get(rr, 1)] = rr
            rr += 1
        missing = [a for a in ROWS if a not in found]
        if missing:
            fail(f'sheet row {r} (bars {[n for _, n in nums]}): reading stopped before '
                 + ', '.join(repr(m) for m in missing)
                 + f'. Look at column A around sheet row {r + 2 + len(found)} - a label '
                 'is probably missing or misspelt, and everything below it is skipped.')
        blocks.append({'row': r, 'bars': bars, 'rows': found, 'end': end})

    # contiguous bar numbering
    seq = [n for b in blocks for n, _, _ in b['bars']]
    if seq != list(range(1, len(seq) + 1)):
        gaps = [n for n in range(1, (max(seq) if seq else 0) + 1) if n not in seq]
        dup = sorted({n for n in seq if seq.count(n) > 1})
        fail(f'bar numbering is not 1..{len(seq)}'
             + (f'; missing {gaps}' if gaps else '')
             + (f'; repeated {dup}' if dup else ''))

    # the cells themselves
    grid, muted = {}, set()
    for b in blocks:
        for src in ROWS:
            rr = b['rows'].get(src)
            if rr is None:
                continue
            for n, c, ln in b['bars']:
                for k in range(ln * 4):
                    grid[(src, n, k)] = get(rr, c + k)
                    if get(rr, c + k) and ital(rr, c + k) and (size(rr, c + k) or 9) == 9:
                        muted.add((src, n, k))
    return blocks, grid, muted


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    if not os.path.exists(src):
        sys.exit(f'no such file: {src}')

    print(f'reading {src}')
    blocks, grid, muted = parse(src)
    bl = {n: ln for b in blocks for n, _, ln in b['bars']}
    print(f'  {len(blocks)} blocks, {len(bl)} bars, {len(muted)} muted strikes')
    nonfour = [(n, l) for n, l in sorted(bl.items()) if l != 4]
    print(f'  bars not in 4: {nonfour if nonfour else "none"}')
    for row, bars, tag in notes:
        print(f'  note in the label cell, sheet row {row} (bars {bars}): {tag!r} - kept, ignored')

    T = json.load(open(TIMING))
    want = [b['bars'] for b in T['blocks']]
    got = [[n for n, _, _ in b['bars']] for b in blocks]
    if want != got:
        for i, (w, g) in enumerate(zip(want, got)):
            if w != g:
                fail(f'block {i + 1} groups bars {g}, but the timing file has {w}. '
                     f'The structure changed, so the timing needs re-deriving - '
                     f'this build will not guess. Ask Claude to re-measure.')
                break
        else:
            fail(f'the sheet has {len(got)} blocks, the timing file has {len(want)}.')

    if problems:
        print('\nSTOPPED. Nothing was written.\n')
        for p in problems:
            print('  * ' + p)
        print()
        sys.exit(1)

    page = open(PAGE, encoding='utf-8').read()
    m = re.search(r'^const DATA = (\{.*\});$', page, re.M)
    if not m:
        sys.exit(f'could not find the data line in {PAGE}')
    D = json.loads(m.group(1))

    changed = 0
    diffs = []
    for blk, tb in zip(D['blocks'], T['blocks']):
        blk['bars'], blk['t0'], blk['t1'] = tb['bars'], tb['t0'], tb['t1']
        blk['lens'] = [bl[n] for n in tb['bars']]
        out, mut = {}, {}
        for lab in ROWS:
            seqv, mi, k = [], [], 0
            for n in tb['bars']:
                for i in range(bl[n] * 4):
                    seqv.append(grid.get((lab, n, i), ''))
                    if (lab, n, i) in muted:
                        mi.append(k)
                    k += 1
            old = blk['cells'].get(lab, [])
            changed += sum(1 for a, b2 in zip(seqv, old) if a != b2) + abs(len(seqv) - len(old))
            for i, (a, b2) in enumerate(zip(seqv, old)):
                if a != b2:
                    k = i
                    for n in tb['bars']:
                        if k < bl[n] * 4:
                            diffs.append((n, k / 4 + 1, lab, b2, a)); break
                        k -= bl[n] * 4
            out[lab] = seqv
            if mi:
                mut[lab] = mi
        blk['cells'], blk['mut'] = out, mut

    new = page[:m.start()] + 'const DATA = ' + json.dumps(D, separators=(',', ':')) + ';' + page[m.end():]
    if new == page:
        print('\nNo change - the page already matches the sheet.')
        sys.exit(3)
    open(PAGE, 'w', encoding='utf-8').write(new)
    print(f'\nwrote {os.path.relpath(PAGE, REPO)}  -  {changed} cells differ\n')
    from collections import Counter
    if diffs:
        by = Counter(d[2] for d in diffs)
        print('  by part: ' + ', '.join(f'{k} {v}' for k, v in by.most_common()))
        print('  by bar : ' + ', '.join(str(b) for b in sorted({d[0] for d in diffs})))
        print()
        print(f'  {"bar":>5} {"beat":>5}  {"part":<20} {"was":>6} -> now')
        for d in sorted(diffs)[:40]:
            print(f'  {d[0]:>5} {d[1]:>5.2f}  {d[2]:<20} {d[3]!r:>6} -> {d[4]!r}')
        if len(diffs) > 40:
            print(f'  ... and {len(diffs) - 40} more')
    print('\nOpen the page to check it, then:  ./deploy.sh "what you changed"')


if __name__ == '__main__':
    main()
