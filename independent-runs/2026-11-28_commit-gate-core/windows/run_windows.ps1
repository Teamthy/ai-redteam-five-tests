# Second independent run of commit-gate-core REPRODUCE.md, Windows PowerShell.
# Runs section 2b verbatim (guide_section_2b.ps1), then the same import check and
# issue 33 probe as the Linux run, then writes a receipt and SHA256 checksums.
#
# Usage, from this folder, in Windows PowerShell 5.1 or PowerShell 7:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\run_windows.ps1
# Read this file and guide_section_2b.ps1 first. Nothing here needs an API key,
# and nothing is uploaded anywhere: results stay in the output folder it prints.

$ErrorActionPreference = "Continue"
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$probe   = Join-Path (Split-Path -Parent $here) "scripts\gap_probe.py"
$stamp   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$out     = Join-Path $HOME ("commit-gate-windows-run-" + $stamp)
$logs    = Join-Path $out "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
Copy-Item (Join-Path $here "guide_section_2b.ps1") $out

function Write-Utf8($path, $text) {
    [System.IO.File]::WriteAllText($path, ($text -join "`n") + "`n", (New-Object System.Text.UTF8Encoding $false))
}

# 1. Environment facts for the receipt
$os      = Get-CimInstance Win32_OperatingSystem
$osLine  = "$($os.Caption) $($os.Version) build $($os.BuildNumber), $($os.OSArchitecture)"
$psExe   = (Get-Process -Id $PID).Path
$psLine  = "PowerShell $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
$gitLine = (git --version) 2>&1 | Out-String
$pyLine  = (python --version) 2>&1 | Out-String
Write-Utf8 (Join-Path $logs "environment.log") @(
    "OS: $osLine", "Shell: $psLine", "Git: $($gitLine.Trim())", "python on PATH: $($pyLine.Trim())"
)

# 2. The guide's own block, unchanged, in a child process so its `exit` and
#    $env:PYTHONPATH stay inside it. stdout and stderr are captured to files.
$stdout = Join-Path $logs "guide_2b.stdout.log"
$stderr = Join-Path $logs "guide_2b.stderr.log"
$proc = Start-Process -FilePath $psExe -Wait -PassThru -NoNewWindow `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"' + (Join-Path $out "guide_section_2b.ps1") + '"')) `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$guideExit = $proc.ExitCode
$guideOut  = Get-Content $stdout -Raw

# The guide does not print its temp folder; pip show prints the venv location.
$testRoot = $null
if ($guideOut -match "Location:\s*(.+?)\\venv\\") { $testRoot = $Matches[1].Trim() }
$passed = "unknown"; $failed = "0"
if ($guideOut -match "(\d+) passed") { $passed = $Matches[1] }
if ($guideOut -match "(\d+) failed") { $failed = $Matches[1] }
$build  = "unknown"; $pytest = "unknown"
$blocks = $guideOut -split "---"
foreach ($b in $blocks) {
    if ($b -match "Name:\s*build\s")  { if ($b -match "Version:\s*(\S+)") { $build  = $Matches[1] } }
    if ($b -match "Name:\s*pytest\s") { if ($b -match "Version:\s*(\S+)") { $pytest = $Matches[1] } }
}
$pyVer = "unknown"
if ($guideOut -match "Python (\d+\.\d+\.\d+)") { $pyVer = $Matches[1] }

# 3. pip version, import check and issue 33 probe, using the guide's own venv
$pipVer = "unknown"
if ($testRoot) {
    $repo = Join-Path $testRoot "repo"
    $py   = Join-Path $testRoot "venv\Scripts\python.exe"
    $pt   = Join-Path $testRoot "venv\Scripts\pytest.exe"
    $pipVer = (& $py -m pip --version) 2>&1 | Out-String
    $pipVer = ($pipVer.Trim() -split " ")[1]

    $files = @("tests/test_authorize.py", "tests/test_beau_failure_classes.py")
    $env:PYTHONPATH = $null
    Push-Location $repo
    $check = @()
    $check += "== python -m pytest, no PYTHONPATH"
    $check += ((& $py -m pytest @files -q -p no:cacheprovider) 2>&1 | Out-String).Trim()
    $check += "== pytest console script"
    $check += ((& $pt @files -q -p no:cacheprovider) 2>&1 | Out-String).Trim()
    $check += "== python -I -m pytest"
    $check += ((& $py -I -m pytest @files -q -p no:cacheprovider) 2>&1 | Out-String).Trim()
    Pop-Location
    Write-Utf8 (Join-Path $logs "collection_check.log") $check

    $gap = (& $py -I $probe $repo) 2>&1 | Out-String
    Write-Utf8 (Join-Path $logs "gap_probe.log") $gap.Trim()
}

# 4. Replace the machine-specific folders in the logs before anything is shared
$userHome = $HOME
foreach ($f in Get-ChildItem $logs -File) {
    $t = Get-Content $f.FullName -Raw
    if ($null -eq $t) { continue }
    if ($testRoot) { $t = $t.Replace($testRoot, '$TEST_ROOT') }
    $t = $t.Replace($userHome, '$HOME')
    if ($env:USERNAME -and $env:USERNAME.Length -ge 4) { $t = $t.Replace($env:USERNAME, '$USER') }
    Write-Utf8 $f.FullName $t.TrimEnd()
}

# 5. Receipt in the guide's format
$mismatch = "none"
if ($guideExit -ne 0) { $mismatch = "guide block exited $guideExit; see logs/guide_2b.stderr.log" }
Write-Utf8 (Join-Path $out "RECEIPT_windows.txt") @(
    "Guide revision (commit SHA from the guide permalink): 0b66c5e44fccd564a62388c5e433760a5088d162",
    "Tested SHA: 610d155232fbc3f590ed40656e48403ef4d20dcf",
    "OS and version: $osLine",
    "Python version: $pyVer",
    "pip version: $pipVer (the guide does not print it; read afterwards with python -m pip --version)",
    "build version: $build",
    "pytest version: $pytest",
    "Exact commands: REPRODUCE.md section 2b, verbatim (guide_section_2b.ps1), run by run_windows.ps1 under $psLine",
    "Tests passed: $passed",
    "Tests failed: $failed",
    "Other test totals / skipped: see logs/guide_2b.stdout.log",
    "Mismatch or failure (quote exactly, or ""none""): $mismatch",
    "Run by: Olusanya Timothy, outside reviewer, $stamp"
)

# 6. Checksums in sha256sum format, so `sha256sum -c` works on Linux or macOS too
$sums = @()
foreach ($f in Get-ChildItem $out -Recurse -File | Where-Object { $_.Name -ne "SHA256SUMS" } | Sort-Object FullName) {
    $rel = "./" + $f.FullName.Substring($out.Length + 1).Replace("\", "/")
    $sums += ((Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower() + "  " + $rel)
}
Write-Utf8 (Join-Path $out "SHA256SUMS") $sums

Write-Host ""
Write-Host "Guide exit code: $guideExit   passed: $passed   failed: $failed"
Write-Host "Results: $out"
if ($testRoot) { Write-Host "Guide temp folder (delete when done): $testRoot" }
