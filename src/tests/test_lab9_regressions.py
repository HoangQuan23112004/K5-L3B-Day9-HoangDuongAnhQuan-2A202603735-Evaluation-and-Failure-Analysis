"""Regression cases from traces and report-integrity attacks."""
import copy
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize("claim,bug,grader", [
    ("C-002", "ticket_trust", "DbFactKept"),
    ("C-014", "pre_deducted", "RefundAmountCorrect"),
    ("C-013", "pre_deducted", "ProposalAmountCorrect"),
    ("C-008", "misreport", "ReplyAmountCorrect"),
    ("C-014", "misreport", "ReplyAmountCorrect"),
])
def test_trace_regression_and_fixed_control(claim, bug, grader):
    from lab8.shapes import SHAPES
    from lab9 import graders
    from lab9.trace_case import investigate
    from lab9.variant_agent import make_shape

    name = f"regression_{bug}"
    SHAPES[name] = make_shape(name, {"no_override", bug})
    evaluator = getattr(graders, grader)()
    for shape, expected in ((name, False), ("fixed", True)):
        case = investigate(shape, claim, 11)
        result = evaluator.evaluate(SimpleNamespace(output=case["trial"], expected_output=case["label"]))
        assert result.value is expected, result.reason


@pytest.mark.parametrize("text", ["Đã hoàn 35.000đ.", "Đã hoàn phí 35,000 VND.", "Hoàn 35000 VNĐ."])
def test_reply_metric_accepts_equivalent_currency_formats(text):
    from lab9.graders import ReplyAmountCorrect

    trial = {"events": [{"kind": "reply", "payload": {"text": text}}],
             "snapshot": {"refund_vnd": 35000}, "result": {"status": "resolved"}}
    assert ReplyAmountCorrect().evaluate(SimpleNamespace(output=trial)).value is True


def test_reply_metric_does_not_accept_unverifiable_resolved_reply():
    from lab9.graders import ReplyAmountCorrect

    trial = {"events": [{"kind": "reply", "payload": {"text": "Đã hoàn tiền."}}],
             "snapshot": {"refund_vnd": 35000}, "result": {"status": "resolved"}}
    assert ReplyAmountCorrect().evaluate(SimpleNamespace(output=trial)).value is False


@pytest.mark.parametrize("attack", ["duplicate", "evaluator", "row_nan", "summary", "relabel", "ratchet_ci"])
def test_advanced_integrity_rejects_hidden_evidence(attack):
    from lab9.gate import integrity_check

    spec = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "kind": "capability",
            "blocking": True, "threshold": {"min": 0.8, "no_significant_drop": True}}]}
    base = {"manifest": {"items": 2, "seeds": [11, 22]}, "evaluator_failures": [],
            "metrics": {"pass_rate": 1.0}, "rows": [
                {"item_id": i, "seed": s, "pass_rate": True, "slices": ["adversarial"]}
                for i in ("E-001", "E-002") for s in (11, 22)]}
    pr, changed = copy.deepcopy(base), copy.deepcopy(spec)
    if attack == "duplicate":
        pr["rows"][1] = copy.deepcopy(pr["rows"][0])
    elif attack == "evaluator":
        pr["evaluator_failures"] = ["grader crashed"]
    elif attack == "row_nan":
        pr["rows"][0]["pass_rate"] = float("nan")
    elif attack == "summary":
        pr["rows"][0]["pass_rate"] = False
    elif attack == "relabel":
        pr["rows"][0]["slices"] = []
    else:
        changed["metrics"][0]["threshold"].pop("no_significant_drop")
    assert integrity_check(pr, base, changed, spec)


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 1), (5, 2, 6), (5, 2, 0), (5.0, 2, 1)])
def test_advanced_pass_estimators_reject_invalid_counts(args):
    from lab9.stats import pass_at_k, pass_hat_k

    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)
