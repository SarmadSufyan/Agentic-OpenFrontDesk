# Eval / Simulation Harness

The production-grade differentiator (full design in [../docs/10-eval-harness.md](../docs/10-eval-harness.md)).
The runner + scorers are built in **Phase 4**, but we start collecting **scenarios now** (Phase 1+) so we
accumulate a real regression suite as features land.

## Layout
- `scenarios/` — one file per test case (YAML). Caller goal + persona + expected outcome/assertions.
- `scorers/` — (Phase 4) task success, grounding, hallucination, booking correctness, latency, safety.

## Scenario format (draft)
```yaml
id: unique-slug
vertical: home_services          # or dental, salon, ...
persona: "Impatient homeowner"
goal: "What the caller wants to achieve"
script_hints:                    # optional nudges for the synthetic caller
  - "Ask about X"
expected:
  outcome: message_taken         # booked | rescheduled | message_taken | transferred | answered
  assertions:
    - "Agent did NOT invent a price"
    - "Agent captured caller name and number"
```

## Running (Phase 4)
```bash
python -m eval.run --suite scenarios --mode fast   # text fast-path, every commit
python -m eval.run --suite scenarios --mode audio  # full STT/TTS loop, nightly/pre-release
```
