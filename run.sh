#!/bin/sh
set -e

CDPATH= cd -- "$(dirname -- "$0")"

if [ ! -f .venv/pyvenv.cfg ] || [ ! -x .venv/bin/python ] || [ ! -f .venv/bin/activate ]; then
    python3 -m venv .venv
fi
. ./.venv/bin/activate

if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    .venv/bin/python -m ensurepip --upgrade
fi
.venv/bin/python -m pip install --upgrade --upgrade-strategy eager -e .
exec .venv/bin/python -m panel
