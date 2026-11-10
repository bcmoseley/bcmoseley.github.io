# Rebuilding a gamelan page from its spreadsheet

From the repository root:

```
./refresh.sh ~/Downloads/Pendet\ Pengaksama.xlsx
./refresh.sh ~/Downloads/Cendrawasih.xlsx
./deploy.sh "what you changed"
```

The script picks the right builder from the filename.

Download the sheet from Google with **File → Download → Microsoft Excel (.xlsx)**.
It has to be `.xlsx`. A CSV carries no formatting, and the muted strikes are
stored as *italics* — exporting CSV silently throws all eight of them away.

Nothing needs installing. The sheet reader is plain Python 3 standard library.

---

## What gets replaced, and what doesn't

Only the notation. The page's prose, layout, player, parts panel and
shift-click range playback are left exactly as they are, so you can keep
editing the page by hand between rebuilds.

**The timing never comes from the sheet.** It lives in `_build/timing_pendet.json`
and was measured from the recording — gong and kajar detection, corrected by
hand against anchors. The sheet's own section timestamps ("2:54", "0:32") are
approximate and disagree with the recording; the Pengecet really starts at
2:53.2, not 2:54. If the timing is ever rebuilt from a beat map it reintroduces
a 1.07 second error from bar 84 onward. Leave that file alone unless you are
deliberately re-measuring.

---

## The checks

The build stops and writes nothing unless all of these pass. Each one exists
because it caught a real mistake:

| check | what it caught |
|---|---|
| every part is present and labelled | a deleted row label in the Cendrawasih sheet, which silently dropped every part below it |
| bar numbers run 1..N, none missing or repeated (Pendet) | an annotation in the label cell that made two bars vanish |
| each bar spans a whole number of beats | — |
| the block grouping matches the timing file (Pendet) | a structural change published with the old, now-wrong timing |
| each section has the bar count the timing file expects (Cendrawasih) | the same, for a piece whose timing is anchors rather than per-block times |

When a check fails it names the sheet row to look at.

A block is found by its `beat` row, **not** by the word `bar` above it. That
cell is free for notes — "Other recordings don't play these bars" and the like.
The build reports any such note and ignores it. This matters: an earlier version
keyed on the word `bar`, and an annotation there made it skip two bars entirely.

What the checks can't catch is a wrong note that is still a plausible note. Open
the page and look at it before deploying.

---

## When the structure changes

If you add, remove or relengthen bars, the build will stop with a message like:

```
block 31 groups bars [60, 61], but the timing file has [61, 62].
```

That is working as intended. The timing map is anchored to measured points in
the recording, and when the bar structure moves, those anchors need re-deriving
against the audio — which is a judgement call, not arithmetic. Ask Claude to
re-measure, and the timing file gets updated alongside the notation.

Changing a bar's *length* without changing the block grouping (m82 going from
3/4 to 4/4, say) passes: each block keeps its measured start and end, and only
the division inside it changes.

---

## The two pieces differ

**Pendet** numbers bars 1..117 straight through, and its timing is a measured
start and end for every block, so `timing_pendet.json` lists blocks.

**Cendrawasih** numbers bars within each section, plays three sections three
times, and its timing is six measured anchors with a piecewise-linear map
between them. So `timing_cendrawasih.json` lists each section's length and
repeat count, and the knot positions. A section changing length moves the
knots, which is what the bar-count check guards.

Cendrawasih's sheet has no bar-number row at all, and one block's `beat` label
is missing, so blocks are found by their runs of instrument rows rather than by
any label. An unlabelled row *between* parts is an error — the build can't tell
which part it is. An unlabelled row *below* the last part is reported and
ignored; there is one at sheet row 120 that has been there all along.

Watch out for one spreadsheet habit: typing `1/3` into a cell makes Google
store a **date**. The reader renders those back using the sheet's own format
code, so a byar pair stays `1/3` rather than becoming `46025`.

---

## Files

```
refresh.sh                      run this; picks the builder from the filename
_build/sheet.py                 reads .xlsx with the standard library:
                                values, italics, and date-formatted cells
_build/build_pendet.py          parse, check, merge timing, rewrite the page
_build/build_cendrawasih.py     the same, for the sectioned piece
_build/timing_pendet.json       measured timing, per block. Not from the sheet.
_build/timing_cendrawasih.json  measured anchors and section lengths.
```

`_build/` starts with an underscore, so Jekyll ignores it and none of it is
published.
