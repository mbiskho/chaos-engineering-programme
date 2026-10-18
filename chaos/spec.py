from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

FAULTS = {"pod-kill", "network-delay", "network-partition", "dns-error", "cpu-stress"}


@dataclass
class Condition:
    name: str
    query: str          # PromQL returning one number
    op: str             # "<" | "<=" | ">" | ">="
    threshold: float


@dataclass
class Experiment:
    name: str
    hypothesis: str
    environment: str                 # staging | production
    namespace: str
    selector: dict[str, str]         # pod labels
    fault: str
    params: dict = field(default_factory=dict)
    duration_seconds: int = 120
    max_targets: int = 1
    recovery_seconds: int = 60
    steady_state: list[Condition] = field(default_factory=list)
    abort_if: list[Condition] = field(default_factory=list)
    owner: str = ""


class SpecError(ValueError):
    pass


def load(path: str | Path) -> Experiment:
    raw = yaml.safe_load(Path(path).read_text())
    raw["steady_state"] = [Condition(**c) for c in raw.get("steady_state", [])]
    raw["abort_if"] = [Condition(**c) for c in raw.get("abort_if", [])]
    exp = Experiment(**raw)
    problems = validate(exp)
    if problems:
        raise SpecError(f"{path}: " + "; ".join(problems))
    return exp


def validate(e: Experiment) -> list[str]:
    p = []
    if e.fault not in FAULTS:
        p.append(f"unknown fault {e.fault!r}")
    if len(e.hypothesis.split()) < 6:
        p.append("hypothesis must state an expected, measurable outcome")
    if not e.steady_state:
        p.append("at least one steady_state condition is required")
    if not e.abort_if:
        p.append("at least one abort_if condition is required")
    if not e.selector:
        p.append("selector is required: never target a whole namespace")
    if e.duration_seconds > 900:
        p.append("duration over 15 minutes: split it into smaller experiments")
    if e.environment == "production" and e.max_targets > 1:
        p.append("production experiments start at max_targets: 1")
    if not e.owner:
        p.append("owner is required (who to call if it goes wrong)")
    for c in e.steady_state + e.abort_if:
        if c.op not in {"<", "<=", ">", ">="}:
            p.append(f"{c.name}: bad operator {c.op!r}")
    return p
