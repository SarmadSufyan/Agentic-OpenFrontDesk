"""Eval CLI.

python -m eval --validate          # load + list scenarios (no LLM/DB needed) — used in CI
python -m eval --run               # run scenarios in text mode (needs GROQ_API_KEY + seeded DB)
python -m eval --run --tenant demo
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from eval.schema import load_scenarios


def main() -> None:
    ap = argparse.ArgumentParser(prog="eval", description="OpenFrontDesk eval harness")
    ap.add_argument("--validate", action="store_true", help="Load + list scenarios (no LLM/DB)")
    ap.add_argument(
        "--run", action="store_true", help="Run scenarios in text mode (needs LLM key + DB)"
    )
    ap.add_argument("--tenant", default="demo", help="Tenant slug to run against")
    args = ap.parse_args()

    scenarios = load_scenarios()
    if not args.run:
        print(f"Loaded {len(scenarios)} scenario(s):")
        for s in scenarios:
            print(
                f"  - {s.id:<22} vertical={s.vertical or '-':<13} expect={s.expected.outcome or '-'}"
            )
        print("\nOK: all scenarios valid." if scenarios else "No scenarios found.")
        return

    from eval.runner import run_suite

    failures = asyncio.run(run_suite(scenarios, tenant_slug=args.tenant))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
