$ErrorActionPreference = "Stop"
$target = "610d155232fbc3f590ed40656e48403ef4d20dcf"
$testRoot = Join-Path $env:TEMP ("commit-gate-repro-" + [guid]::NewGuid().ToString("N"))
$repo = Join-Path $testRoot "repo"
$venv = Join-Path $testRoot "venv"
New-Item -ItemType Directory -Path $testRoot | Out-Null
git clone --no-checkout https://github.com/LalaSkye/commit-gate-core.git $repo
if ($LASTEXITCODE -ne 0) { throw "git clone failed with exit code $LASTEXITCODE" }
git -C $repo fetch origin $target
if ($LASTEXITCODE -ne 0) { throw "git fetch failed with exit code $LASTEXITCODE" }
git -C $repo checkout --detach $target
if ($LASTEXITCODE -ne 0) { throw "git checkout failed with exit code $LASTEXITCODE" }
$actual = (git -C $repo rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw "git rev-parse failed with exit code $LASTEXITCODE" }
$actual = $actual.Trim()
if ($actual -ne $target) { throw "Expected $target, got $actual" }
$worktreeStatus = git -C $repo status --porcelain
if ($LASTEXITCODE -ne 0) { throw "git status failed with exit code $LASTEXITCODE" }
if ($worktreeStatus) { throw "Checkout is not clean" }
git -C $repo rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "git rev-parse failed with exit code $LASTEXITCODE" }
python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "python -m venv failed with exit code $LASTEXITCODE" }
$python = Join-Path $venv "Scripts\python.exe"
& $python --version
if ($LASTEXITCODE -ne 0) { throw "python --version failed with exit code $LASTEXITCODE" }
& $python -m pip install --upgrade build pytest
if ($LASTEXITCODE -ne 0) { throw "pip install failed with exit code $LASTEXITCODE" }
& $python -m pip show build pytest
if ($LASTEXITCODE -ne 0) { throw "pip show failed with exit code $LASTEXITCODE" }
Push-Location $repo
$env:PYTHONPATH = "src"
& $python -m pytest tests/test_authorize.py tests/test_beau_failure_classes.py -q
$testExit = $LASTEXITCODE
Pop-Location
if ($testExit -ne 0) { exit $testExit }
