#!/bin/bash
#
# Rebuild a gamelan page from its spreadsheet.
#
#   ./refresh.sh ~/Downloads/Pendet\ Pengaksama.xlsx
#
# Download the sheet from Google first: File -> Download -> Microsoft Excel.
# It has to be .xlsx, not .csv -- the muted strikes live in the cell italics
# and a CSV throws those away.
#
# Nothing is written unless the sheet passes every check. If it stops, it
# says which sheet row to look at.
#
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -lt 1 ]; then
    echo "usage: ./refresh.sh <sheet.xlsx>"
    echo
    echo "Download from Google Sheets with File -> Download -> Microsoft Excel (.xlsx)."
    exit 1
fi

SRC="$1"
case "$SRC" in
    *.csv) echo "That's a CSV. Download as .xlsx instead, or the muted strikes are lost."; exit 1;;
esac

# which page does this sheet belong to?
case "$(basename "$SRC" | tr '[:upper:]' '[:lower:]')" in
    *cendrawasih*) BUILD=_build/build_cendrawasih.py ;;
    *)             BUILD=_build/build_pendet.py ;;
esac

if [ ! -f "$BUILD" ]; then
    echo "No builder for that sheet yet ($BUILD). Only Pendet is set up so far."
    exit 1
fi

set +e
python3 "$BUILD" "$SRC"
RC=$?
set -e
[ $RC -eq 3 ] && exit 0          # builder: nothing to do
[ $RC -ne 0 ] && exit $RC        # builder: checks failed, it already explained

echo
if [ -n "$(git status --porcelain gamelan/ 2>/dev/null)" ]; then
    echo "The page changed. Open it in a browser to check it, then:"
    echo "    ./deploy.sh \"what you changed\""
fi
