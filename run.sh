#!/bin/bash
# macOS: normally use "The Data Application.app". This file starts the same window from a terminal and keeps the messages visible.
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3.9 or newer was not found. Install it from https://www.python.org/downloads/ and start this file again."
  read -r -p "Press Enter to close this window..."
  exit 1
fi
exec "$PY" the_data_app.py gui
