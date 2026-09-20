"""Entrypoint for the voice agent worker: `ofd-agent` (e.g. `ofd-agent dev`).

Delegates to the LiveKit CLI. See ofd.agent.worker and docs/04-voice-pipeline.md.
"""

from __future__ import annotations


def main() -> None:
    from ofd.agent.worker import run

    run()


if __name__ == "__main__":
    main()
