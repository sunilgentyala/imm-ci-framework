# Changelog

All notable changes to the IMM-CI Self-Assessment Tool are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-05-03

### Initial release — companion to SmartNets 2026 CyberSec CIIA paper

This is the first public release of the IMM-CI Self-Assessment Tool, published
alongside the acceptance of the companion paper at SmartNets 2026.

### Added
- `imm_ci_assessor.py` — core scoring engine with weighted rubrics for three
  IMM-CI dimensions: IAM Capabilities, Zero Trust Posture, and PQC Readiness
- Per-dimension normalized scoring calibrated against cumulative capability sums
  derived from IMM-CI Table II (paper Section XII)
- Composite level computation using weakest-link principle (NIST SP 800-207 §2)
- Level 2→3 stall pattern detection — flags the most common industrial operator
  failure mode identified in the paper
- YAML-driven configuration for repeatable, auditable assessments
- Interactive questionnaire mode (`--interactive`) for teams without a config file
- JSON report output (`--json-out`) for integration with GRC tooling
- `config/sample_org.yaml` — Lakeshore Metropolitan Water Authority baseline
  profile (IMM-CI Level 2), mirroring the paper's pilot starting state
- `tests/test_imm_ci_assessor.py` — 27 unit and integration tests covering:
  - Dimension scoring (rubric weights, score clamping, gap detection)
  - Composite level (weakest-link principle)
  - Stall detection
  - Named profiles (Level 1, Level 2, Lakeshore baseline, Lakeshore post-pilot)
  - JSON serialization
  - Pilot improvement delta (all three dimensions improve, composite advances)
- `tests/lakeshore_baseline_result.json` — live tool output against the sample
  config, citable as a companion artifact in the paper

### Test results
```
45 passed in 0.03s  (Python 3.11-3.14, pytest 8.x+)
```

### Known limitations
- PQC readiness rubric reflects FIPS 203/204 (August 2024 finalization).
  Update rubric weights if NIST issues additional PQC standards post-2026.
- Scoring thresholds are calibrated for the five IMM-CI levels as defined in
  the paper. Organizations with partial capability adoption may sit at level
  boundaries; treat boundary scores (within ±3 points of a threshold) as
  requiring manual judgment.
- Interactive mode does not persist responses; use `--config` with a YAML file
  for repeatable, auditable assessments.
