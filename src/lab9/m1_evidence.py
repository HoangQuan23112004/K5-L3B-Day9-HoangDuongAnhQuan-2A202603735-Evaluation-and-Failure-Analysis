"""Reproduce M1 coverage and controls, without modifying any Lab 8 source.

Run from src/: python -m lab9.m1_evidence
The JSON captures full events (unlike the truncated trace_case console output).
Labels remain in labels_v1.json; this file is evidence, not an eval baseline.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9.evalset import FAILURE_MODES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

SWITCHES = {
    "FM-01": "leaky_trace", "FM-02": "ignore_denied",
    "FM-03": "ticket_trust", "FM-04": "sum_parts",
    "FM-05": "pre_deducted", "FM-06": "stale_clause",
    "FM-07": "sibling_refund", "FM-08": "misreport",
}


def capture(shape: str, claim: str) -> dict:
    trial = investigate(shape, claim, 11)["trial"]
    return {"shape": shape, "claim_id": claim, "seed": 11,
            "run_id": trial["result"]["run_id"],
            "result": trial["result"], "snapshot": trial["snapshot"],
            "unexpected_rows": trial["unexpected_rows"],
            "lab8_pass": trial["lab8_pass"], "lab8_reason": trial["lab8_reason"],
            "events": [{"step": i, **e} for i, e in enumerate(trial["events"], 1)]}


def main() -> int:
    utf8_stdio()
    for fm, switch in SWITCHES.items():
        SHAPES[f"m1_{switch}"] = make_shape(f"m1_{switch}", {"no_override", switch})
    # C-001 has a single clause, so use rounding rather than summing for FM-04.
    SHAPES["m1_round_down"] = make_shape("m1_round_down", {"no_override", "round_down"})
    controls, probes = [], []
    for claim, modes in FAILURE_MODES.items():
        control = capture("fixed", claim)
        controls.append(control)
        print(f"fixed {claim}@11: {'PASS' if control['lab8_pass'] else 'FAIL'}")
        for fm in modes:
            shape = "m1_round_down" if (claim, fm) == ("C-001", "FM-04") else f"m1_{SWITCHES[fm]}"
            probe = {"failure_mode": fm, **capture(shape, claim)}
            # Outcome-only PASS can hide FM-08; inspect the reply as well.
            replies = [e["payload"]["text"] for e in probe["events"] if e["kind"] == "reply"]
            amounts = re.findall(r"hoàn ([\d.]+)đ", " ".join(replies))
            probe["reply_ledger_mismatch"] = any(
                int(a.replace(".", "")) != probe["snapshot"]["refund_vnd"] for a in amounts)
            probe["observed_failure"] = not probe["lab8_pass"] or probe["reply_ledger_mismatch"]
            probes.append(probe)
            print(f"  {fm} {shape}: {probe['lab8_reason']}; ledger={probe['snapshot']['refund_vnd']}")
    out = Path("data/eval/m1_trace_evidence.json")
    out.write_text(json.dumps({"seed": 11, "fixed_controls": controls, "probes": probes},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(controls)} controls, {len(probes)} probes")
    observed = {p["failure_mode"] for p in probes if p["observed_failure"]}
    return 0 if all(c["lab8_pass"] for c in controls) and observed == set(SWITCHES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
