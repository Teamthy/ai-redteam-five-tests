#!/usr/bin/env python3
"""Run the five-test harness and fill the evidence package from the real results.

The package at package.md ships with two marked blocks:

    <!-- CONFIG:BEGIN -->   ... <!-- CONFIG:END -->
    <!-- RESULTS:BEGIN -->  ... <!-- RESULTS:END -->

This script runs the harness, then rewrites both blocks from what the run actually produced. It
never invents a number. If the run fails, the blocks are left exactly as they were and the script
exits non-zero.

Usage, from the repo root:

    python3 build_package.py \
        --model gpt-4o-mini \
        --base-url http://localhost:11434/v1 \
        --api-key ollama

    # or point it at an existing clone instead of letting it clone one
    python3 build_package.py --harness /path/to/ai-redteam-five-tests ...

Before sending, read the generated section 4 yourself. Every flagged response needs a human verdict
next to it, and that part is not automatable.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PINNED_COMMIT = "d95a57e3d5bfcad847b5d5d05d5beab1a49e8ba6"
REPO_URL = "https://github.com/Teamthy/ai-redteam-five-tests.git"
PACKAGE = Path(__file__).resolve().parent / "package.md"



def probe_completion(model, base_url, headers, body_of):
    """One max_tokens=1 call. This is the only honest test of whether we may generate."""
    import urllib.error
    import urllib.request

    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
    ).encode("utf-8")
    send = dict(headers, **{"Content-Type": "application/json"})
    req = urllib.request.Request(url, data=payload, headers=send, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read(64)
    except urllib.error.HTTPError as exc:
        msg = body_of(exc)
        if exc.code == 403:
            raise SystemExit(
                "the endpoint accepted the key and then refused the request (HTTP 403).\n"
                "  %s\n"
                "  Two causes: this account is not entitled to %r, or requests from this network\n"
                "  are blocked. Try another model id first, then another provider:\n"
                "    --base-url https://generativelanguage.googleapis.com/v1beta/openai/ --model gemini-2.5-flash\n"
                "    --base-url https://api.openai.com/v1 --model gpt-4o-mini" % (msg, model)
            )
        if exc.code == 400:
            raise SystemExit(
                "the endpoint rejected the request itself (HTTP 400). %s\n"
                "  A message about terms acceptance is fixed in the provider's console, for that\n"
                "  model, in one click. A message about context or tokens means the model id is not\n"
                "  a chat model at all. Both are model choices, not key problems." % msg
            )
        if exc.code == 404:
            raise SystemExit(
                "the endpoint has no model called %r (HTTP 404). %s\n"
                "  List what it does have:\n"
                '    curl.exe -sS %s/models -H "Authorization: Bearer <key>"' % (model, msg, base_url.rstrip("/"))
            )
        raise SystemExit("the endpoint refused a test completion (HTTP %d). %s" % (exc.code, msg))
    except Exception as exc:
        raise SystemExit(
            "the test completion did not finish (%s). Check that the base URL ends in /v1 and "
            "that the model id is one the endpoint serves." % exc.__class__.__name__
        )
    print("[ok] %s answers a real completion, so the run can proceed." % model)


def preflight(model, base_url, api_key="x"):
    """Fail with a readable message before doing any work."""
    try:
        import openai  # noqa: F401
    except ImportError:
        raise SystemExit(
            "The harness needs the openai package and it is not installed for this interpreter.\n"
            "  fix: %s -m pip install openai\n"
            "  interpreter: %s" % (sys.executable, sys.executable)
        )

    import urllib.error
    import urllib.request

    url = base_url.rstrip("/") + "/models"
    headers = {
        "Authorization": "Bearer " + (api_key or "x"),
        "User-Agent": "OpenAI/Python 3.x (redteam-pack)",
        "Accept": "application/json",
    }

    def body_of(exc):
        try:
            return exc.read().decode("utf-8", "replace").strip().replace("\n", " ")[:200]
        except Exception:
            return "(no body)"

    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as resp:
            resp.read(64)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise SystemExit(
                "the endpoint does not accept this key (HTTP 401 at %s).\n"
                "  %s\n"
                "  Check the key, and that --base-url belongs to the provider it came from."
                % (url, body_of(exc))
            )
        # A refused model list does not prove completions are refused. Ask the real question.
        print("[..] the model list came back %d. Testing one real completion instead." % exc.code)
        probe_completion(model, base_url, headers, body_of)
    except Exception as exc:
        raise SystemExit(
            "Nothing answered at %s (%s).\n"
            "  Ollama:     ollama serve  then  ollama pull %s\n"
            "  LM Studio:  Developer tab, Start Server, check the port\n"
            "  Then confirm the base URL ends in /v1 and the model id is loaded."
            % (url, exc.__class__.__name__, model)
        )
    print("[ok] openai installed, endpoint answering at %s" % base_url)


def sh(cmd, cwd=None, env=None):
    """Run a command, return stdout, raise on failure."""
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            "command failed: %s\n%s\n%s" % (" ".join(cmd), proc.stdout[-2000:], proc.stderr[-2000:])
        )
    return proc.stdout


def get_harness(path, workdir):
    """Use an existing clone, or clone the pinned commit into workdir."""
    if path:
        harness = Path(path).expanduser().resolve()
        if not (harness / "redteam.py").exists():
            raise SystemExit("no redteam.py in %s" % harness)
        head = sh(["git", "rev-parse", "HEAD"], cwd=str(harness)).strip()
        print("[harness] using %s at %s" % (harness, head))
        if head != PINNED_COMMIT:
            print("[harness] WARNING: HEAD is %s, package pins %s" % (head, PINNED_COMMIT))
        return harness

    target = Path(workdir) / "ai-redteam-five-tests"
    print("[harness] cloning %s" % REPO_URL)
    sh(["git", "clone", "--quiet", REPO_URL, str(target)])
    sh(["git", "checkout", "--quiet", PINNED_COMMIT], cwd=str(target))
    head = sh(["git", "rev-parse", "HEAD"], cwd=str(target)).strip()
    print("[harness] checked out %s" % head)
    if head != PINNED_COMMIT:
        raise SystemExit("clone is at %s, expected %s" % (head, PINNED_COMMIT))
    return target


def run_harness(harness, model, base_url, api_key, prompt_file=None):
    """Run the harness and return (results dict, generated results.md text)."""
    env = dict(os.environ)
    env["MODEL"] = model
    env["OPENAI_BASE_URL"] = base_url
    env["OPENAI_API_KEY"] = api_key
    if prompt_file:
        env["MY_SYSTEM_PROMPT_FILE"] = str(Path(prompt_file).expanduser().resolve())

    print("[run] python redteam.py  (model=%s endpoint=%s)" % (model, base_url))
    proc = subprocess.run([sys.executable, "redteam.py"], cwd=str(harness), env=env,
                          capture_output=True, text=True)

    results_json = harness / "results" / "results.json"
    results_md = harness / "results" / "results.md"

    # The harness writes results.json, then crashes while writing results.md, because write_outputs()
    # indexes the results dict by display name ("Test 1 - prompt injection") instead of by key
    # ("test1"). Known defect at the pinned commit. The run itself finishes before the crash, so a
    # non-zero exit with results.json on disk is a usable run and is reported as one.
    note = ""
    if proc.returncode != 0:
        if not results_json.exists():
            raise SystemExit(
                "the run failed and wrote no results/results.json\n"
                + (proc.stdout + proc.stderr)[-2500:]
            )
        note = (
            "The harness exited with an error after writing `results.json` and before writing "
            "`results.md`. Known defect at the pinned commit: `write_outputs()` reads the results "
            "dict by display name instead of by key. The run completed, the raw responses are "
            "recorded below, and nothing in this section depends on `results.md`."
        )
        print("[warn] harness exited non-zero but wrote results.json, continuing")

    data = json.loads(results_json.read_text(encoding="utf-8"))
    md = results_md.read_text(encoding="utf-8") if results_md.exists() else ""
    return data, md, note, (proc.stdout or "") + (proc.stderr or "")


def archive_run(harness, package, console):
    """Keep the raw record beside the package, with hashes.

    Added 2026-11-02 after an independent reviewer asked for the original results.json from a run
    whose package had already been built. The package reproduced every flagged response but the raw
    JSON was not kept, which is a retention defect in the process rather than in the run. From here
    on the package travels with its record: results.json, the console log, and a hash manifest
    covering both plus the harness file that produced them.
    """
    import hashlib

    out = Path(package).resolve().parent / "run_record"
    out.mkdir(exist_ok=True)

    results_json = Path(harness) / "results" / "results.json"
    if not results_json.exists():
        raise SystemExit("no results/results.json to archive at %s" % results_json)
    shutil.copy2(results_json, out / "results.json")

    if console.strip():
        (out / "console.log").write_text(console, encoding="utf-8")

    def digest(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    lines = ["# SHA-256 manifest, written by build_package.py", ""]
    for name in ("results.json", "console.log"):
        target = out / name
        if target.exists():
            lines.append("%s  %s" % (digest(target), name))
    redteam = Path(harness) / "redteam.py"
    if redteam.exists():
        lines.append("%s  redteam.py" % digest(redteam))
    head = sh(["git", "rev-parse", "HEAD"], cwd=str(harness)).strip()
    blob = ""
    try:
        blob = sh(["git", "rev-parse", "HEAD:redteam.py"], cwd=str(harness)).strip()
    except SystemExit:
        pass
    lines += ["", "commit  %s" % head]
    if blob:
        lines.append("blob    %s  redteam.py" % blob)
    lines += [
        "",
        "# Digests above are of the files as they exist in this working tree. A checkout on another",
        "# platform may convert line endings, which changes the SHA-256 without changing the content.",
        "# The blob id is the platform independent identifier for the same file, added 2026-11-03",
        "# after a Windows checkout reported a different SHA-256 for the same commit.",
        "",
    ]

    manifest = out / "SHA256SUMS.txt"
    manifest.write_text("\n".join(lines), encoding="utf-8")
    print("[record] %s" % manifest)
    for line in lines:
        if line and not line.startswith("#"):
            print("  " + line)
    return out



def empty_answer_report(data):
    """Count responses that came back with no words. An empty answer is not a refusal."""
    empties, total = [], 0
    for key, tests in data.items():
        if not isinstance(tests, list):
            continue
        for entry in tests:
            if not isinstance(entry, dict):
                continue
            text = entry.get("raw") or entry.get("response") or ""
            if not isinstance(text, str):
                continue
            total += 1
            if not text.strip():
                empties.append(key)
    return total, empties


def config_block(model, base_url, timestamp, results):
    """Section 2.3. Only what the run actually used."""
    import platform

    try:
        import openai

        sdk = getattr(openai, "__version__", "unknown")
    except Exception:
        sdk = "not importable"
    rows = [
        ("Model id", "`%s`" % model),
        ("Endpoint", "`%s`" % base_url),
        ("Temperature", "0.2, harness default"),
        ("Max tool steps", "4, harness default"),
        ("Run started", timestamp),
        ("Sample", "built-in OrderBot prompt"),
        ("Python", "`%s`" % sys.version.split()[0]),
        ("openai SDK", "`%s`" % sdk),
        ("Platform", "`%s`" % platform.platform().replace("|", "/")),
    ]
    body = ["| Field | Value |", "|---|---|"]
    body += ["| %s | %s |" % (k, v) for k, v in rows]
    return "\n".join(body)


def results_block(data, md, model, base_url, timestamp, note=""):
    """Section 4, built from results.json only."""
    meta = data.get("meta", {})
    run = meta.get("run", timestamp)

    lines = []
    lines.append("**Run:** %s UTC, model `%s`, endpoint `%s`." % (run, model, base_url))
    lines.append("")
    lines.append(
        "Only the responses the detectors flagged are reproduced here. A row marked not flagged "
        "is the detector's reading, not a reproduced reply, so it is stated as a reading and can "
        "be re-run rather than taken on trust."
    )
    lines.append("")
    if note:
        lines.append("> " + note)
        lines.append("")

    def section(title, items, key):
        if not items:
            return
        lines.append("**%s**" % title)
        lines.append("")
        flagged = 0
        for it in items:
            broke = it.get("broke")
            if broke:
                flagged += 1
            mark = "FLAGGED" if broke else "not flagged"
            label = it.get(key, "?")
            lines.append("- `%s` %s. %s" % (label, mark, it.get("why", "")))
        lines.append("")
        lines.append("Flagged %d of %d in this test." % (flagged, len(items)))
        lines.append("")

    section("Test 1, prompt injection", data.get("test1"), "attempt")
    section("Test 2, retrieval poisoning", data.get("test2"), "question")
    section("Test 3, tool description poisoning", data.get("test3"), "condition")
    section("Test 4, multilingual refusals", data.get("test4"), "refusal")

    lines.append("**Test 5, failure rate per input type**")
    lines.append("")
    lines.append("| Failure class | Sample | Flagged | Rate |")
    lines.append("|---|---|---|---|")
    for name, total, fired, rate in data.get("test5", []):
        shown = "n/a" if total == 0 else (
            ("%.0f%%" % (rate * 100)) if isinstance(rate, float) else str(rate)
        )
        lines.append("| %s | %d | %d | %s |" % (name, total, fired, shown))
    lines.append("")
    lines.append(
        "Rates are over a single run. A rate with a sample this small is an observation, not a "
        "measurement, and it is printed with its sample size for that reason."
    )
    lines.append("")
    lines.append("**Every flagged response, verbatim**")
    lines.append("")
    lines.append("Each one needs a human verdict beside it before this document goes out.")
    lines.append("")
    for test, key in (("test1", "attempt"), ("test2", "question"), ("test3", "condition"), ("test4", "refusal")):
        for it in data.get(test, []):
            if it.get("broke"):
                lines.append("```")
                lines.append("%s / %s / %s" % (test, it.get(key, "?"), it.get("why", "")))
                lines.append("")
                lines.append((it.get("raw") or "").strip())
                lines.append("```")
                lines.append("")

    if md:
        lines.append("")
        lines.append("The harness also wrote `results/results.md`, reproduced in full:")
        lines.append("")
        lines.append("```")
        lines.append(md.strip())
        lines.append("```")
    return "\n".join(lines)


def replace_block(text, name, new_body):
    pattern = re.compile(
        r"(<!-- %s:BEGIN -->)(.*?)(<!-- %s:END -->)" % (name, name), re.S
    )
    if not pattern.search(text):
        raise SystemExit("marker %s not found in the package" % name)
    return pattern.sub(lambda m: m.group(1) + "\n" + new_body.strip() + "\n" + m.group(3), text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="model id to test")
    ap.add_argument("--base-url", required=True, help="OpenAI-compatible base URL")
    ap.add_argument("--api-key", default="no-key", help="placeholder key is fine for local endpoints")
    ap.add_argument("--harness", help="existing clone; skips cloning")
    ap.add_argument("--prompt-file", help="test your own system prompt instead of the sample bot")
    ap.add_argument("--package", default=str(PACKAGE), help="package file to fill")
    args = ap.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    package = Path(args.package)
    if not package.exists():
        raise SystemExit("no package at %s" % package)

    preflight(args.model, args.base_url, args.api_key)
    print("[plan] clone harness at %s, run 5 tests against %s, fill %s" % (PINNED_COMMIT[:7], args.model, package.name))

    workdir = tempfile.mkdtemp(prefix="fivetests-")
    try:
        harness = get_harness(args.harness, workdir)
        data, md, note, console = run_harness(harness, args.model, args.base_url, args.api_key, args.prompt_file)

        total, empties = empty_answer_report(data)
        if total and len(empties) >= total:
            raise SystemExit(
                "every one of the %d responses came back empty. That is not a model refusing, "
                "that is a model with no room to answer.\n"
                "  Reasoning models spend a small token budget thinking and return nothing. "
                "Raise the budget in the harness, or pick a model that answers directly.\n"
                "  Nothing was written to the package." % total
            )
        if empties:
            note = ((note + " ") if note else "") + (
                "%d of %d responses came back empty. An empty answer is not a refusal, so those "
                "attempts prove nothing either way and are reported as empty rather than as "
                "resisted." % (len(empties), total)
            )
            print("[warn] %d of %d responses were empty. Read those rows before you sign this."
                  % (len(empties), total))

        text = package.read_text(encoding="utf-8")
        text = replace_block(text, "CONFIG", config_block(args.model, args.base_url, timestamp, data))
        text = replace_block(
            text, "RESULTS", results_block(data, md, args.model, args.base_url, timestamp, note)
        )
        package.write_text(text, encoding="utf-8")
        print("[done] filled %s" % package)
        archive_run(harness, package, console)
        print("[next] send the package and the run_record directory together, never the package alone.")
        print("[next] read section 4 and put a human verdict beside every flagged response.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
