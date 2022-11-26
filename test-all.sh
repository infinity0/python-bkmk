#!/bin/bash

shopt -s nullglob globstar

scriptdir="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$scriptdir/src"

PYTHON=python3
if ! $PYTHON -c "from bkmk.xbel import from_fmt_time; from_fmt_time('2022-11-22T20:26:25.067968Z')" 2>/dev/null; then
  PYTHON=python3.11
fi

set -x
$PYTHON test/bookmarks-test.py data/**/*.{html,json,xbel} data-priv*/**/*.{html,json,xbel}
