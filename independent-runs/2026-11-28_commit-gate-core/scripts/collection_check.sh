#!/usr/bin/env bash
# Shows that tests/test_authorize.py only collects under `python -m pytest`.
# Usage: bash collection_check.sh <checkout at 610d155> <venv with pytest>
set -u
repo="$1"; venv="$2"
files="tests/test_authorize.py tests/test_beau_failure_classes.py"
cd "$repo"
echo "== python -m pytest, no PYTHONPATH";  env -i PATH=/usr/bin:/bin "$venv/bin/python" -m pytest $files -q -p no:cacheprovider 2>&1 | tail -1
echo "== pytest console script";           env -i PATH=/usr/bin:/bin "$venv/bin/pytest" $files -q -p no:cacheprovider 2>&1 | grep -E "ModuleNotFoundError|passed|error" | head -2
echo "== python -I -m pytest";             env -i PATH=/usr/bin:/bin "$venv/bin/python" -I -m pytest $files -q -p no:cacheprovider 2>&1 | grep -E "ModuleNotFoundError|passed|error" | head -2
