"""Scenario loading for the eval harness.

A scenario describes a synthetic caller (goal + persona) and what a good outcome looks like.
Files live in eval/scenarios/*.yaml. See eval/README.md and docs/10-eval-harness.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


@dataclass
class Expected:
    outcome: str | None = None
    assertions: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    goal: str
    vertical: str | None = None
    persona: str | None = None
    script_hints: list[str] = field(default_factory=list)
    expected: Expected = field(default_factory=Expected)
    raw: dict = field(default_factory=dict)


def _parse(data: dict) -> Scenario:
    exp = data.get("expected") or {}
    return Scenario(
        id=str(data["id"]),
        goal=str(data.get("goal", "")),
        vertical=data.get("vertical"),
        persona=data.get("persona"),
        script_hints=list(data.get("script_hints") or []),
        expected=Expected(
            outcome=exp.get("outcome"),
            assertions=list(exp.get("assertions") or []),
        ),
        raw=data,
    )


def load_scenarios(directory: Path | str = SCENARIOS_DIR) -> list[Scenario]:
    directory = Path(directory)
    out: list[Scenario] = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "id" not in data:
            raise ValueError(f"Invalid scenario file (needs an 'id'): {path.name}")
        out.append(_parse(data))
    return out
