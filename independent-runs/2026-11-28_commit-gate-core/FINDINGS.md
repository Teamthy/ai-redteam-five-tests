# commit-gate-core: independent run, 28 Nov 2026

Run by Olusanya Timothy, an outside reviewer, using an AI coding agent (Claude) in a fresh cloud Linux sandbox. Nobody from the AlvianTech side was involved.

## Result

The 12 tests reproduce: 12 passed, 0 failed, on Python 3.11.18 and again on Python 3.13.18. Guide revision 4e9e9a5, tested commit 610d155. The receipt is in `RECEIPT.txt`.

## How it was run

- Each run used a fresh `mktemp -d` checkout, exactly as section 2a says. Commands: `scripts/guide_section_2a.sh`, pulled byte for byte out of REPRODUCE.md and run with `bash -x`. Logs: `logs/run_A_python3.13.log` and `logs/run_B_python3.11.log`. In the logs the temp folder appears as `$TEST_ROOT` and the folder holding the python3.11 symlink as `$SHIM311`.
- Before running anything we read `src/commit_gate_core/*.py`, both test files and `tests/conftest.py`. None of them touch the network, the filesystem or subprocesses.
- The environment was cleared with `env -i`. It kept PATH, HOME, LANG and the network proxy settings. No tokens or keys were set.
- Run B's only change was a `python3` symlink to python3.11 placed first on PATH. The Linux block has no hint on picking 3.11; only the Windows block has one.

## Where a stranger trips

1. **The guide doesn't print the pip version.** The receipt asks for it, but the commands run only `pip show build pytest`. Adding `python -m pip --version` would fix it.
2. **`tests/test_authorize.py` collects only under `python -m`.** It imports `src.commit_gate_core.*`, while `test_beau_failure_classes.py` imports `commit_gate_core.*`. The `src.` import resolves only because `python -m pytest` puts the current folder on sys.path. To rerun: `bash scripts/collection_check.sh <checkout> <venv>` (output in `logs/collection_check.log`):
   - `python -m pytest`, no PYTHONPATH: 12 passed. So `PYTHONPATH=src` is redundant; pyproject `pythonpath` and conftest already add it.
   - `pytest`: collection error, `ModuleNotFoundError: No module named 'src'`
   - `python -I -m pytest`: the same error

   Because of the two styles, the two files also load two separate copies of the package. It's harmless here. The catch is that a stranger who types `pytest` sees a red result.
3. Minor: the guide leaves its temp folder behind without saying so.

## Issue 33 gaps, shown on a local copy

We didn't read the issue text itself (GitHub rate-limited the fetch). These probes test the two gaps as Ricky described them. Both are already listed as not built in the README claim boundary, RELEASE_NOTES and CLAIM_BOUNDARY, so this makes them concrete. It doesn't report a bug in anything claimed.

To rerun: `python3.11 -I scripts/gap_probe.py <checkout at 610d155>` (output in `logs/gap_probe.log`). The probe uses the public package only, with the lab key and in-memory ledger shape from the repo's own tests.

1. **No asymmetric signature.** The `HmacSha256Verifier` the gate gets for verifying also has `.sign()`. With it, we minted a new approval for `invoice_999` with a new nonce and a different payload, and the gate returned `AUTHORIZED`.
2. **No durable spent-approval record.** The same signed approval gave:
   - first use: `AUTHORIZED`
   - replay against the same ledger: `DENY:NONCE_REPLAYED` (the control holds)
   - replay against a fresh ledger, as after a restart: `AUTHORIZED`
   - two workers, each with its own ledger: both `AUTHORIZED`

   One-use holds only while one ledger object lives, inside the expiry window. NonceLedger is a Protocol, and every implementation in the tree is in-memory and lives in tests or scripts.

## Not covered

macOS and Windows weren't run. The text of issue 33 wasn't read.
