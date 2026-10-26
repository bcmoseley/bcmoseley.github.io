#!/bin/bash
#
# Deploy the site: show what changed, commit it, push it.
#
#   ./deploy.sh "what you changed"
#
# Run with no message to see the pending changes without committing anything.
#
set -euo pipefail
cd "$(dirname "$0")"

MSG="${1:-}"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "repo    $(pwd)"
echo "branch  $BRANCH"
echo

if [ -n "$(git status --porcelain)" ]; then
    echo "--- changes ---"
    git status --short
    echo
    if [ -z "$MSG" ]; then
        echo "Nothing committed: no message given."
        echo "Run:  ./deploy.sh \"what you changed\""
        exit 1
    fi
    git add -A
    git commit -q -m "$MSG"
    echo "committed: $MSG"
    echo
else
    echo "Working folder is clean, nothing new to commit."
    echo
fi

AHEAD=$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)

if [ "$AHEAD" -eq 0 ]; then
    echo "Nothing to push. GitHub is already up to date."
    exit 0
fi

echo "--- pushing $AHEAD commit(s) ---"
git push
echo
echo "Pushed. GitHub rebuilds the site in a minute or two:"
echo "   https://briancmoseley.com/"
echo "If it doesn't appear, check for a build failure at"
echo "   https://github.com/bcmoseley/bcmoseley.github.io/actions"
