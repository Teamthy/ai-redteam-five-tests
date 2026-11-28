"""Probe the two gaps Ricky Jones listed in issue 33, against a local checkout.

Usage:  python -I gap_probe.py /path/to/commit-gate-core   (checkout at 610d155)

Uses only the public package surface (commit_gate_core) and the same lab key
and in-memory ledger shape the repo's own tests use. Nothing leaves the machine.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                     capture_output=True, text=True, check=True).stdout.strip()
sys.path.insert(0, str(repo / "src"))

from commit_gate_core import CommitGate, HmacSha256Verifier, payload_hash  # noqa: E402

print(f"commit-gate-core HEAD {sha}")
print(f"python {sys.version.split()[0]}")

KEY = b"lab-key-not-for-production"          # same key the repo's tests use
POLICY = "2026-04-27.1"
NOW = datetime(2026, 4, 27, 5, 1, tzinfo=timezone.utc)


class Clock:
    def now(self):
        return NOW


class InMemoryNonceLedger:                   # same shape as tests/test_authorize.py
    def __init__(self):
        self.used, self.owner = set(), {}

    def contains(self, n):
        return n in self.used

    def consume(self, n, d):
        if n in self.used:
            return False
        self.used.add(n)
        self.owner[n] = d
        return True

    def rollback(self, n, d):
        if self.owner.get(n) == d:
            self.used.discard(n)
            self.owner.pop(n, None)


class Audit:
    def __init__(self):
        self.events = []

    def append(self, e):
        self.events.append(dict(e))


def gate(verifier, ledger):
    return CommitGate(verifier=verifier, nonce_ledger=ledger, audit=Audit(),
                      accepted_policy_versions=(POLICY,), clock=Clock())


def record(signer, payload, **over):
    r = {"decision_id": "dr_001", "actor_id": "agent_17", "action": "approve_invoice",
         "object_id": "invoice_778", "environment": "prod",
         "commit_hash": payload_hash(payload), "verdict": "ALLOW",
         "policy_version": POLICY, "issued_at": "2026-04-27T05:00:00Z",
         "expires_at": "2026-04-27T05:05:00Z", "nonce": "nonce_001", "signature": ""}
    r.update(over)
    r["signature"] = signer.sign(r)
    return r


def scope(r):
    return {k: r[k] for k in ("actor_id", "action", "object_id", "environment")}


PAYLOAD = b"invoice-778-body"

# ---------------------------------------------------------------- Gap 1
print("\n[1] No asymmetric signature: whoever can verify can also issue")
verifier = HmacSha256Verifier(KEY)           # the object the gate is given to VERIFY
g = gate(verifier, InMemoryNonceLedger())
evil_payload = b"pay-invoice-999-to-attacker"
forged = record(verifier, evil_payload, decision_id="dr_forged", object_id="invoice_999",
                nonce="nonce_forged")         # minted with the verifier's own sign()
res = g.authorize(forged, evil_payload, **scope(forged))
print(f"    approval minted by the verifying side -> {res.code}")
print(f"    hasattr(verifier, 'sign') = {hasattr(verifier, 'sign')}")
g1 = res.code == "AUTHORIZED"

# ---------------------------------------------------------------- Gap 2a
print("\n[2a] No durable spent-approval record: replay after a restart")
approval = record(verifier, PAYLOAD)
first = gate(verifier, InMemoryNonceLedger()).authorize(dict(approval), PAYLOAD, **scope(approval))
same_proc = None
ledger = InMemoryNonceLedger()
g_a = gate(verifier, ledger)
g_a.authorize(dict(approval), PAYLOAD, **scope(approval))
same_proc = g_a.authorize(dict(approval), PAYLOAD, **scope(approval))
after_restart = gate(verifier, InMemoryNonceLedger()).authorize(dict(approval), PAYLOAD, **scope(approval))
print(f"    first use                         -> {first.code}")
print(f"    replay, same ledger               -> {same_proc.code}")
print(f"    replay, fresh ledger (restart)    -> {after_restart.code}")
g2a = same_proc.code == "DENY:NONCE_REPLAYED" and after_restart.code == "AUTHORIZED"

# ---------------------------------------------------------------- Gap 2b
print("\n[2b] Same approval at two workers that each hold their own ledger")
w1 = gate(verifier, InMemoryNonceLedger()).authorize(dict(approval), PAYLOAD, **scope(approval))
w2 = gate(verifier, InMemoryNonceLedger()).authorize(dict(approval), PAYLOAD, **scope(approval))
print(f"    worker 1 -> {w1.code}   worker 2 -> {w2.code}")
g2b = w1.authorized and w2.authorized

print("\nSUMMARY")
print(f"    gap 1 shown  (verifier key mints approvals): {g1}")
print(f"    gap 2 shown  (one-use approval accepted twice across ledgers): {g2a and g2b}")
print(f"    control held (same-ledger replay refused): {same_proc.code == 'DENY:NONCE_REPLAYED'}")
