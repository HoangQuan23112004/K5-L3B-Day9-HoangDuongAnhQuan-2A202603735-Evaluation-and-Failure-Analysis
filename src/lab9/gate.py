"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    for field, identity in (("metrics", lambda m: m["id"]),
                            ("slices", lambda m: (m["name"], m["metric"]))):
        entries = spec.get(field, [])
        if len({identity(m) for m in entries}) != len(entries):
            problems.append(f"duplicate {field} entries in spec")
        for entry in entries:
            thresholds = entry.get("threshold", {}) if field == "metrics" else entry
            for key in ("min", "max", "max_increase"):
                if key in thresholds and (not isinstance(thresholds[key], (int, float))
                                           or not math.isfinite(thresholds[key])):
                    problems.append(f"invalid spec threshold {identity(entry)}/{key}")
    if problems:
        return problems
    pairs = {}
    tags = {}
    derived = {"pass_5", "cost_per_success"} | {
        f"pass_{kind}_{k}" for kind in ("at", "hat") for k in spec.get("pass_k", [])}
    for name, report in (("PR", pr), ("baseline", base)):
        manifest = report.get("manifest", {})
        rows = report.get("rows", [])
        metrics = report.get("metrics", {})
        seeds = manifest.get("seeds", [])
        items = manifest.get("items", 0)
        if (type(items) is not int or not isinstance(seeds, list)
                or any(type(s) is not int for s in seeds)
                or not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows)
                or not isinstance(metrics, dict)):
            return [f"{name}: invalid report structure"]
        if not rows or not seeds or len(set(seeds)) != len(seeds) or items < 1:
            problems.append(f"{name}: invalid or empty manifest/rows")
        if len(rows) != items * len(seeds):
            problems.append(f"{name}: row count differs from items x seeds")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator_failures is nonempty")
        for mid, value in metrics.items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: nonfinite/missing metric {mid}")
        for metric in spec["metrics"]:
            mid = metric["id"]
            if mid not in metrics:
                problems.append(f"{name}: missing summary metric {mid}")
        keys = [(r.get("item_id"), r.get("seed")) for r in rows]
        counts = Counter(keys)
        if any(n != 1 for n in counts.values()):
            problems.append(f"{name}: duplicate (item_id, seed)")
        ids = {k[0] for k in keys}
        if len(ids) != items or set(keys) != {(i, s) for i in ids for s in seeds}:
            problems.append(f"{name}: incomplete item x seed grid")
        if "seeds" in spec and set(seeds) != set(spec["seeds"]):
            problems.append(f"{name}: manifest seeds differ from spec")
        pairs[name] = set(keys)
        tags[name] = {}
        row_ids = [m["id"] for m in spec["metrics"]
                   if m["id"] not in derived and (m["id"] in GRADERS
                       or any(m["id"] in r for r in rows))]
        for row in rows:
            item = row.get("item_id")
            slices = row.get("slices", [])
            if not isinstance(slices, list) or any(not isinstance(s, str) for s in slices):
                problems.append(f"{name}: invalid slice tags for {item}")
                slices = []
            frozen = frozenset(slices)
            if item in tags[name] and tags[name][item] != frozen:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            tags[name][item] = frozen
            for mid in row_ids:
                if type(row.get(mid)) is not bool:
                    problems.append(f"{name}: missing/invalid row value {item}/{mid}")
            if "cost" in row and (not isinstance(row["cost"], (int, float))
                                   or not math.isfinite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid cost for {item}")
        # Recompute available aggregates so editing summary numbers cannot hide failures.
        for mid in row_ids:
            if rows and all(type(r.get(mid)) is bool for r in rows):
                is_safety = next(m for m in spec["metrics"] if m["id"] == mid).get("kind") == "safety"
                total = sum(r[mid] for r in rows)
                expected = total if is_safety else round(total / len(rows), 4)
                value = metrics.get(mid)
                if isinstance(value, (int, float)) and not math.isclose(value, expected, abs_tol=1e-8):
                    problems.append(f"{name}: summary {mid} disagrees with rows")
        if rows and all(type(r.get("pass_rate")) is bool and "cost" in r for r in rows):
            from lab9.eval import aggregate
            recomputed = aggregate(rows, row_ids, k_values=spec.get("pass_k", []))
            for mid in derived & metrics.keys():
                value, expected = metrics[mid], recomputed.get(mid)
                if expected is None or not isinstance(value, (int, float)) or not math.isclose(value, expected, abs_tol=1e-8):
                    problems.append(f"{name}: derived metric {mid} disagrees with rows")
    if pairs["PR"] != pairs["baseline"]:
        problems.append("PR item/seed set differs from baseline")
    if tags["PR"] != tags["baseline"]:
        problems.append("PR slice membership differs from baseline")
    if base_spec is not None:
        if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
            problems.append("eval-set version changed: build a new baseline")
        else:
            for field, key in (("metrics", lambda m: m["id"]),
                               ("slices", lambda m: (m["name"], m["metric"]))):
                current = {key(m): m for m in spec.get(field, [])}
                for old in base_spec.get(field, []):
                    identity = key(old)
                    new = current.get(identity)
                    if new is None:
                        problems.append(f"ratchet: removed {field} {identity}")
                        continue
                    if old.get("blocking") and not new.get("blocking"):
                        problems.append(f"ratchet: disabled blocking {identity}")
                    a, b = (old.get("threshold", {}), new.get("threshold", {})) if field == "metrics" else (old, new)
                    for threshold in ("min", "max", "max_increase"):
                        if threshold in a and (threshold not in b or
                            (b[threshold] < a[threshold] if threshold == "min" else b[threshold] > a[threshold])):
                            problems.append(f"ratchet: loosened {identity}/{threshold}")
                    if a.get("no_significant_drop") and not b.get("no_significant_drop"):
                        problems.append(f"ratchet: removed no_significant_drop {identity}")
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identity = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        failed, note = not a or set(a) != set(b), ""
        value = sum(a.values()) / len(a) if a else None
        if value is not None and "min" in entry and value < entry["min"]:
            failed = True
        if a and set(a) == set(b) and entry.get("no_significant_drop"):
            keys = sorted(a)
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            failed |= hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identity)
        lines.append(f"  {identity:<36} {value!s:<8} {note} {'BLOCK' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
