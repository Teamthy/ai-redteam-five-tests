# Independent run of commit-gate-core, 28 Nov 2026

The guide's 12 tests pass on Python 3.11 and on 3.13. I found two places a stranger trips, and a short script shows the two issue 33 gaps. Allow about 10 minutes to check all of this yourself.

## What's here

| File | What it is |
|---|---|
| `RECEIPT.txt` | The REPRODUCE.md receipt, filled in |
| `FINDINGS.md` | What I ran, what happened, where a stranger trips, and the issue 33 probes |
| `scripts/guide_section_2a.sh` | Section 2a of REPRODUCE.md at 4e9e9a5, verbatim |
| `scripts/collection_check.sh` | Shows that test_authorize.py collects only under `python -m` |
| `scripts/guide_section_2b.ps1` | Section 2b of REPRODUCE.md at 4e9e9a5, verbatim, for the Windows run |
| `scripts/collection_check.ps1` | Windows version of `collection_check.sh` |
| `scripts/gap_probe.py` | Shows both issue 33 gaps (about 150 lines, standard library plus the package) |
| `logs/` | Output of each run. The temp folder appears as `$TEST_ROOT` |
| `WINDOWS_RUNBOOK.md` | Steps for a second run of the same guide in Windows PowerShell |
| `SHA256SUMS` | Checksums for every file above |

## Check it in 10 minutes (Linux or macOS, Python 3.11+)

Read the three scripts first. They're short.

```bash
sha256sum -c SHA256SUMS                       # 1. files are as sent

bash -x scripts/guide_section_2a.sh 2>&1 | tee my_run.log   # 2. the guide itself, ~1 min
tail -1 my_run.log                            #    expect: 12 passed

root=$(sed -n 's/^+ test_root=//p' my_run.log | head -1)      # the guide's temp folder
bash scripts/collection_check.sh "$root/repo" "$root/venv"      # 3. expect: 12 passed, then 2x No module named 'src'
python3 -I scripts/gap_probe.py "$root/repo"                    # 4. expect: gap 1 True, gap 2 True, control True
```

Compare your output with `logs/`. Step 2 needs network access to GitHub and PyPI; nothing else does. When you're done, `rm -rf "$root"` cleans up.

## Scope

This covers only the pinned authorise-only candidate, 610d155. The README claim boundary at that commit applies in full. The issue 33 probes run against a local checkout only.
