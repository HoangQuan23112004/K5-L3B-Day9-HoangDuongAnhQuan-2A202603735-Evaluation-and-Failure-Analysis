"""Ablation: identical workflow with exactly one extra MockLLM draft call."""

from lab8.schemas import RunResult
from lab8.shapes.workflow import _run_claim


def run_claim(
    claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None,
) -> RunResult:
    return _run_claim(
        claim_id, seed=seed, store_path=store_path, crash_at=crash_at,
        shape="workflow_draft", draft=True,
    )
