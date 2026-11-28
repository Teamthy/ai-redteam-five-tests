# Shows whether tests/test_authorize.py collects outside `python -m pytest`.
# Windows counterpart of collection_check.sh.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File collection_check.ps1 <checkout at 610d155> <venv with pytest>
param([Parameter(Mandatory)][string]$Repo, [Parameter(Mandatory)][string]$Venv)
$ErrorActionPreference = "Continue"
$files = @("tests/test_authorize.py", "tests/test_beau_failure_classes.py")
$python = Join-Path $Venv "Scripts\python.exe"
$pytest = Join-Path $Venv "Scripts\pytest.exe"
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Push-Location $Repo
function Show($label, $exe, $extra) {
    "== $label"
    $out = & $exe @extra @files -q -p no:cacheprovider 2>&1 | ForEach-Object { "$_" }
    $hits = $out | Select-String -Pattern "ModuleNotFoundError|passed|error" | Select-Object -First 2
    if ($hits) { $hits | ForEach-Object { $_.Line } } else { $out | Select-Object -Last 1 }
}
Show "python -m pytest, no PYTHONPATH" $python @("-m", "pytest")
Show "pytest console script"           $pytest @()
Show "python -I -m pytest"             $python @("-I", "-m", "pytest")
Pop-Location
