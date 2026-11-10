# Rebuilding a gamelan page from its spreadsheet

From the repository root:

```
./refresh.sh ~/Downloads/Pendet\ Pengaksama.xlsx
./deploy.sh "what you changed"
```

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
| every block has all ten instrument rows | a deleted row label in the Cendrawasih sheet, which silently dropped every part below it |
| bar numbers run 1..N with none missing or repeated | — |
| each bar spans a whole number of beats | — |
| the sheet's block grouping matches the timing file | a structural change that would otherwise have been published with the old, now-wrong timing |

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

## Files

```
refresh.sh                 run this
_build/sheet.py            reads .xlsx with the standard library, values + italics
_build/build_pendet.py     parse, check, merge timing, rewrite the page
_build/timing_pendet.json  measured timing, keyed by bar. Not from the sheet.
```

`_build/` starts with an underscore, so Jekyll ignores it and none of it is
published.
