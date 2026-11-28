# Windows run (second independent run)

This folder is for running the same guide on Windows PowerShell, which REPRODUCE.md still lists as untested. It runs section 2b exactly as written, then repeats the Linux checks. You end up with a receipt, logs and checksums in the same shape as the Linux run.

**Not run yet.** Nothing in this folder is a result until the files from step 3 are added.

## You need

- Windows 10 or 11 with Windows PowerShell 5.1 or PowerShell 7
- Git for Windows on PATH
- Python 3.11 or later on PATH as `python` (check with `python --version`)
- Network access to GitHub and PyPI

## 1. Get the files and read them (3 minutes)

```powershell
git clone https://github.com/Teamthy/ai-redteam-five-tests.git
cd ai-redteam-five-tests\independent-runs\2026-11-28_commit-gate-core\windows
Get-Content .\guide_section_2b.ps1    # section 2b of REPRODUCE.md at 0b66c5e, verbatim
Get-Content .\run_windows.ps1         # the wrapper: runs 2b, then the checks, then the receipt
```

## 2. Run it (about 2 minutes)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_windows.ps1
```

`-ExecutionPolicy Bypass` applies to this one process only and doesn't change your system setting. When the run finishes, the last lines print the exit code, the pass and fail counts, and the results folder (`$HOME\commit-gate-windows-run-<date>`).

If `python` is the wrong version, the guide's own advice is to use `py -3.11 -m venv $venv` for the venv step. Make that one edit in `guide_section_2b.ps1`, and note it on the "Exact commands" line of the receipt.

## 3. Check and keep the output (5 minutes)

In the results folder:

| File | What to check |
|---|---|
| `RECEIPT_windows.txt` | Every field is filled in. Fix anything that reads "unknown" by hand from the logs |
| `logs/guide_2b.stdout.log` | Ends with `12 passed` for a match with Linux |
| `logs/guide_2b.stderr.log` | Git progress lines are normal here. Anything else goes on the "Mismatch" line, quoted exactly |
| `logs/collection_check.log` | Linux gave 12 passed, then `No module named 'src'` twice |
| `logs/gap_probe.log` | Linux gave gap 1 True, gap 2 True, control True |
| `SHA256SUMS` | Written last. If you change any file afterwards, regenerate it with the snippet below |

Before sharing, search the logs for your username and any folder names you don't want public. The script replaces `$HOME`, the guide's temp folder and your username, but it can't catch everything.

If you edit the receipt or a log, regenerate the checksums from inside the results folder:

```powershell
$out = (Get-Location).Path
Get-ChildItem -Recurse -File | Where-Object Name -ne "SHA256SUMS" | Sort-Object FullName | ForEach-Object {
  (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower() + "  ./" + $_.FullName.Substring($out.Length + 1).Replace("\", "/")
} | Set-Content -Encoding ascii SHA256SUMS
```

Copy the results folder here as `windows/results/` and open a PR. Delete the guide's temp folder (the script prints its path) when you're done.

## What a Windows result shows

It covers the two documented test files at the pinned commit, on your Windows setup. The README claim boundary at that commit applies in full, as it does for the Linux run.
