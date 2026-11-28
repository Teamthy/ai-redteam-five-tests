# Second run on Windows PowerShell

This repeats the same guide on Windows, using section 2b of REPRODUCE.md. It keeps the Linux run's approach: the guide's commands run unchanged, the output goes to a log, the receipt follows the guide's format, and every file gets a SHA-256 checksum. Allow about 20 minutes.

Each block below is pasted into one PowerShell window, in order. Keep that window open from start to finish so the variables carry over.

## Before you start

- Windows 10 or 11, with Windows PowerShell 5.1 or PowerShell 7
- Python 3.11 or later (`python --version` or `py -0` lists what is installed)
- Git for Windows
- Network access to GitHub and PyPI

## 1. Get this package and check it

```powershell
$ErrorActionPreference = "Continue"
$work = Join-Path $HOME "commit-gate-windows-run"
git -c core.autocrlf=false clone https://github.com/Teamthy/ai-redteam-five-tests $work
$pkg = Join-Path $work "independent-runs\2026-11-28_commit-gate-core"
Set-Location $pkg

# Check every file against SHA256SUMS. Expect all lines OK.
Get-Content SHA256SUMS | ForEach-Object {
    $want, $path = $_ -split '\s+', 2
    $got = (Get-FileHash -Algorithm SHA256 $path.TrimStart('.', '/')).Hash.ToLower()
    if ($got -eq $want) { "OK      $path" } else { "FAILED  $path" }
}
```

The `core.autocrlf=false` setting stops Git for Windows from changing line endings, which would break every checksum. If any line still says FAILED, stop and record which file.

## 2. Read the guide and the script

Open REPRODUCE.md on GitHub and click **Copy permalink** (or press `y`) so the address shows a commit SHA. That SHA is your **guide revision**. Write it down.

Then read `scripts\guide_section_2b.ps1` beside section 2b of the guide. It should be the same block, line for line. It was copied from guide revision `4e9e9a5`, and section 2b is unchanged at `0b66c5e`. If your revision's block differs, paste the block from your revision into that file and note it in the receipt.

## 3. Run the guide

```powershell
$out = Join-Path $pkg "windows"
New-Item -ItemType Directory -Force -Path (Join-Path $out "logs") | Out-Null
$runLog = Join-Path $out "logs\run_W.log"

$start = Get-Date
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\guide_section_2b.ps1 2>&1 |
    ForEach-Object { "$_" } | Tee-Object -Variable lines
"exit code: $LASTEXITCODE" | Tee-Object -Variable tail
($lines + $tail) | Set-Content -Encoding UTF8 $runLog
```

The last pytest line should read `12 passed`. The guide runs in its own PowerShell process, so a failure there does not close this window. If setup stops before pytest runs, the log has the step and its message. Copy that message exactly into the receipt.

If `python` points at a version older than 3.11, open `scripts\guide_section_2b.ps1`, change `python -m venv $venv` to `py -3.11 -m venv $venv` as the guide allows, and run this step again. Record that change.

## 4. Record the versions the guide does not print

```powershell
$testRoot = Get-ChildItem $env:TEMP -Directory -Filter "commit-gate-repro-*" |
    Where-Object { $_.CreationTime -ge $start } | Sort-Object CreationTime | Select-Object -Last 1
$testRoot = $testRoot.FullName
$repo = Join-Path $testRoot "repo"
$venv = Join-Path $testRoot "venv"
$py = Join-Path $venv "Scripts\python.exe"

$envLog = Join-Path $out "logs\environment.log"
& {
    "OS: " + (Get-CimInstance Win32_OperatingSystem | ForEach-Object { "$($_.Caption) $($_.Version) $($_.OSArchitecture)" })
    "PowerShell: " + $PSVersionTable.PSVersion
    git --version
    & $py --version
    & $py -m pip --version
    & $py -m pip show build pytest | Select-String "^(Name|Version):"
    "HEAD: " + (git -C $repo rev-parse HEAD)
} 2>&1 | ForEach-Object { "$_" } | Tee-Object -Variable envLines
$envLines | Set-Content -Encoding UTF8 $envLog
```

## 5. Check how the tests collect

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\collection_check.ps1 $repo $venv 2>&1 |
    ForEach-Object { "$_" } | Tee-Object -Variable ccLines
$ccLines | Set-Content -Encoding UTF8 (Join-Path $out "logs\collection_check.log")
```

On Linux this printed `12 passed`, then `No module named 'src'` twice. Record whether Windows matches.

## 6. Run the issue 33 probe

```powershell
& $py -I scripts\gap_probe.py $repo 2>&1 | ForEach-Object { "$_" } | Tee-Object -Variable gpLines
$gpLines | Set-Content -Encoding UTF8 (Join-Path $out "logs\gap_probe.log")
```

Expect `gap 1 shown ... True`, `gap 2 shown ... True` and `control held ... True`.

## 7. Take personal paths out of the logs

The temp folder path contains your Windows user name. This swaps it for `$TEST_ROOT` and your home folder for `$HOME`, as in the Linux logs.

```powershell
Get-ChildItem (Join-Path $out "logs") -Filter *.log | ForEach-Object {
    $t = Get-Content -Raw $_.FullName
    $t = $t.Replace($testRoot, '$TEST_ROOT').Replace($HOME, '$HOME').Replace($env:USERNAME, '$USER')
    Set-Content -Encoding UTF8 -NoNewline $_.FullName $t
}
Select-String -Path (Join-Path $out "logs\*.log") -SimpleMatch $env:USERNAME   # expect no output
```

## 8. Fill in the receipt

This writes the guide's receipt with the fields left open. Fill each one from the logs, and use "unknown" for anything you cannot establish.

```powershell
@"
Guide revision (commit SHA from the guide permalink):
Tested SHA: 610d155232fbc3f590ed40656e48403ef4d20dcf
OS and version:
Python version:
pip version:
build version:
pytest version:
Exact commands: REPRODUCE.md section 2b, verbatim (scripts/guide_section_2b.ps1), run with powershell -NoProfile -ExecutionPolicy Bypass -File
Tests passed:
Tests failed:
Other test totals / skipped:
Mismatch or failure (quote exactly, or "none"):
Run by: Olusanya Timothy, outside reviewer, own Windows machine, $(Get-Date -Format 'd MMM yyyy')
"@ | Set-Content -Encoding UTF8 (Join-Path $out "RECEIPT.txt")
notepad (Join-Path $out "RECEIPT.txt")
```

## 9. Checksums

Run this after the receipt is saved and closed.

```powershell
Set-Location $out
Get-ChildItem -Recurse -File | Where-Object Name -ne "SHA256SUMS" | Sort-Object FullName | ForEach-Object {
    $rel = "./" + (Resolve-Path -Relative $_.FullName).TrimStart('.', '\').Replace('\', '/')
    "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower(), $rel
} | Set-Content -Encoding Ascii SHA256SUMS
Get-Content SHA256SUMS
```

The format matches `sha256sum`, so anyone on Linux or macOS can check it with `sha256sum -c SHA256SUMS` from inside `windows\`.

## 10. Clean up

The `windows\` folder holds the receipt, four logs and SHA256SUMS. Keep it. Then remove the guide's temp folder:

```powershell
Set-Location $HOME
Remove-Item -Recurse -Force $testRoot
```
