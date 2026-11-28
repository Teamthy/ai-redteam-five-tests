set -eu
target=610d155232fbc3f590ed40656e48403ef4d20dcf
test_root="$(mktemp -d)"
git clone --no-checkout https://github.com/LalaSkye/commit-gate-core.git "$test_root/repo"
git -C "$test_root/repo" fetch origin "$target"
git -C "$test_root/repo" checkout --detach "$target"
test "$(git -C "$test_root/repo" rev-parse HEAD)" = "$target"
test -z "$(git -C "$test_root/repo" status --porcelain)"
git -C "$test_root/repo" rev-parse HEAD
python3 -m venv "$test_root/venv"
. "$test_root/venv/bin/activate"
python --version
python -m pip install --upgrade build pytest
python -m pip show build pytest
cd "$test_root/repo"
PYTHONPATH=src python -m pytest tests/test_authorize.py tests/test_beau_failure_classes.py -q
