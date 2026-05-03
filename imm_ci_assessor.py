"""
IMM-CI Self-Assessment Tool
Companion artifact to: "The Metamorphosis of Access: Strategic Imperatives for
Identity 3.0 and Zero Trust Integration in Critical Infrastructure"
SmartNets 2026 - CyberSec CIIA

Authors: Sunil Gentyala, Floriano Caprio -- HCLTech, Dallas TX
Contact: sunil.gentyala@ieee.org

Usage:
    python imm_ci_assessor.py --config config/sample_org.yaml
    python imm_ci_assessor.py --interactive
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    dimension: str
    raw_score: float        # 0-100
    level: int              # 1-5
    gaps: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    org_name: str
    assessment_date: str
    iam_score: DimensionScore
    zt_score: DimensionScore
    pqc_score: DimensionScore
    composite_level: int
    stall_warning: bool
    executive_summary: str
    priority_actions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring rubrics -- derived from IMM-CI Table II (paper Section XII)
# ---------------------------------------------------------------------------

IAM_RUBRIC = {
    "password_only": {"weight": -30, "label": "Password-only auth on any system"},
    "mfa_enforced": {"weight": 20, "label": "MFA enforced for all users"},
    "ldap_ad_integration": {"weight": 10, "label": "LDAP/AD integrated"},
    "partial_abac": {"weight": 10, "label": "Attribute-based access control (partial)"},
    "fido2_deployed": {"weight": 20, "label": "FIDO2/passkeys deployed"},
    "scim_provisioning": {"weight": 15, "label": "SCIM provisioning active"},
    "itdr_deployed": {"weight": 15, "label": "ITDR deployed"},
    "spiffe_spire": {"weight": 15, "label": "SPIFFE/SPIRE for workload identity"},
    "dids_piloted": {"weight": 10, "label": "Decentralized Identifiers piloted"},
    "full_ssi": {"weight": 15, "label": "Full SSI / verifiable credentials"},
    "autonomous_jml": {"weight": 10, "label": "Autonomous JML lifecycle"},
}

ZT_RUBRIC = {
    "perimeter_only": {"weight": -20, "label": "Perimeter-based; implicit internal trust"},
    "network_segmentation": {"weight": 20, "label": "Network segmentation in place"},
    "some_zt_policies": {"weight": 10, "label": "Some Zero Trust policies enforced"},
    "identity_control_plane": {"weight": 20, "label": "Identity is the control plane"},
    "caep_risc_active": {"weight": 15, "label": "CAEP/RISC session signals active"},
    "continuous_evaluation": {"weight": 15, "label": "Continuous trust evaluation"},
    "behavioral_analytics": {"weight": 15, "label": "Behavioral analytics live"},
    "full_zta": {"weight": 15, "label": "Full Zero Trust Architecture"},
    "crypto_attestation_all": {"weight": 10, "label": "Cryptographic attestation on all entities"},
}

PQC_RUBRIC = {
    "classical_only": {"weight": -10, "label": "Classical algorithms only (RSA/ECC), no plan"},
    "crypto_inventory": {"weight": 20, "label": "Cryptographic inventory documented"},
    "migration_plan": {"weight": 20, "label": "PQC migration plan exists"},
    "hybrid_pqc_test": {"weight": 20, "label": "Hybrid classical-PQC in test environments"},
    "mlkem_mldsa_production": {"weight": 25, "label": "ML-KEM / ML-DSA in production (select systems)"},
    "crypto_agility_achieved": {"weight": 25, "label": "Cryptographic agility achieved (algorithm-agnostic IAM)"},
}


# Per-dimension thresholds derived from cumulative capability sums
# normalized against each rubric's max positive weight.
# IAM max positive = 140, ZT max = 120, PQC max = 110.
_DIMENSION_THRESHOLDS: dict[str, list[float]] = {
    "IAM Capabilities":   [15.0, 35.0, 70.0, 85.0],
    "Zero Trust Posture": [15.0, 35.0, 65.0, 82.0],
    "PQC Readiness":      [10.0, 25.0, 65.0, 82.0],
}
_DEFAULT_THRESHOLDS = [15.0, 35.0, 65.0, 82.0]


def _compute_max_positive(rubric: dict) -> float:
    return sum(v["weight"] for v in rubric.values() if v["weight"] > 0) or 1.0


def _score_to_level(normalized: float, dimension: str) -> int:
    thresholds = _DIMENSION_THRESHOLDS.get(dimension, _DEFAULT_THRESHOLDS)
    for level, threshold in enumerate(thresholds, start=1):
        if normalized < threshold:
            return level
    return 5


def _compute_gaps_and_steps(responses: dict, rubric: dict) -> tuple[list[str], list[str]]:
    gaps = []
    steps = []

    enabled = {k for k, v in responses.items() if v}
    disabled = {k for k, v in responses.items() if not v}

    negative_keys = {k for k, v in rubric.items() if v["weight"] < 0}
    positive_keys = {k for k, v in rubric.items() if v["weight"] > 0}

    for k in enabled & negative_keys:
        gaps.append(f"Active gap: {rubric[k]['label']}")
    for k in disabled & positive_keys:
        gaps.append(f"Missing capability: {rubric[k]['label']}")

    # Priority order: highest-weight missing items first
    missing_positive = sorted(
        [(k, rubric[k]["weight"]) for k in disabled & positive_keys],
        key=lambda x: -x[1]
    )
    for k, w in missing_positive[:5]:
        steps.append(f"Implement: {rubric[k]['label']} (impact weight: {w})")

    return gaps, steps


def score_dimension(name: str, responses: dict, rubric: dict) -> DimensionScore:
    raw = sum(
        rubric[k]["weight"] for k, present in responses.items()
        if k in rubric and present
    )
    max_positive = _compute_max_positive(rubric)
    normalized = max(0.0, min(100.0, raw / max_positive * 100))
    level = _score_to_level(normalized, name)
    gaps, steps = _compute_gaps_and_steps(responses, rubric)
    return DimensionScore(dimension=name, raw_score=round(normalized, 1), level=level,
                          gaps=gaps, next_steps=steps)


def compute_composite_level(iam: DimensionScore, zt: DimensionScore, pqc: DimensionScore) -> int:
    # Composite = minimum of the three -- weakest link principle (NIST SP 800-207 §2)
    return min(iam.level, zt.level, pqc.level)


def detect_stall(iam: DimensionScore, zt: DimensionScore, pqc: DimensionScore) -> bool:
    """Flags the L2->L3 stall pattern: IAM at 2, ZT partially above, PQC lagging."""
    return (
        iam.level == 2
        and zt.level <= 3
        and pqc.level <= 2
    )


def generate_summary(result: "AssessmentResult") -> str:
    level_labels = {1: "Foundational", 2: "Structured", 3: "Defined", 4: "Managed", 5: "Optimized"}
    label = level_labels.get(result.composite_level, "Unknown")
    stall_note = (
        " The organization shows the Level 2->3 stall pattern identified in the IMM-CI model. "
        "Vendor coordination, downtime window planning, and FIDO2 HMI compatibility are likely blockers."
        if result.stall_warning else ""
    )
    return (
        f"{result.org_name} assessed at IMM-CI Level {result.composite_level} ({label}). "
        f"IAM: L{result.iam_score.level} | Zero Trust: L{result.zt_score.level} | "
        f"PQC Readiness: L{result.pqc_score.level}.{stall_note}"
    )


# ---------------------------------------------------------------------------
# Assessment orchestration
# ---------------------------------------------------------------------------

def run_assessment(config: dict) -> AssessmentResult:
    org_name = config.get("organization", "Unknown Organization")
    iam_resp = config.get("iam", {})
    zt_resp = config.get("zero_trust", {})
    pqc_resp = config.get("pqc", {})

    iam = score_dimension("IAM Capabilities", iam_resp, IAM_RUBRIC)
    zt = score_dimension("Zero Trust Posture", zt_resp, ZT_RUBRIC)
    pqc = score_dimension("PQC Readiness", pqc_resp, PQC_RUBRIC)

    composite = compute_composite_level(iam, zt, pqc)
    stall = detect_stall(iam, zt, pqc)

    # Priority actions: top 2 from each dimension that are highest impact
    priority = []
    for dim in [iam, zt, pqc]:
        priority.extend(dim.next_steps[:2])

    result = AssessmentResult(
        org_name=org_name,
        assessment_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        iam_score=iam,
        zt_score=zt,
        pqc_score=pqc,
        composite_level=composite,
        stall_warning=stall,
        executive_summary="",
        priority_actions=priority,
    )
    result.executive_summary = generate_summary(result)
    return result


def print_report(result: AssessmentResult) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  IMM-CI ASSESSMENT REPORT")
    print(f"  {result.org_name}  |  {result.assessment_date}")
    print(sep)
    print(f"\n  EXECUTIVE SUMMARY\n  {result.executive_summary}\n")

    for dim in [result.iam_score, result.zt_score, result.pqc_score]:
        print(f"  [{dim.dimension}]  Score: {dim.raw_score}/100  ->  Level {dim.level}")
        if dim.gaps:
            print("    Gaps:")
            for g in dim.gaps[:4]:
                print(f"      - {g}")
        if dim.next_steps:
            print("    Next Steps:")
            for s in dim.next_steps[:3]:
                print(f"      -> {s}")
        print()

    print(f"  COMPOSITE LEVEL: {result.composite_level}/5")
    if result.stall_warning:
        print("  *** L2->L3 STALL PATTERN DETECTED -- see Section XII of IMM-CI paper ***")

    print(f"\n  TOP PRIORITY ACTIONS")
    for i, action in enumerate(result.priority_actions[:6], 1):
        print(f"  {i}. {action}")
    print(f"\n{sep}\n")


def interactive_mode() -> dict:
    """Walk the user through each control question."""
    print("\n=== IMM-CI Interactive Assessment ===\n")
    org_name = input("Organization name: ").strip() or "My Organization"
    config: dict = {"organization": org_name, "iam": {}, "zero_trust": {}, "pqc": {}}

    def ask(section: dict, key: str, label: str) -> None:
        ans = input(f"  [{key}] {label}? (y/n): ").strip().lower()
        section[key] = ans in ("y", "yes", "1", "true")

    print("\n--- IAM Capabilities ---")
    for key, meta in IAM_RUBRIC.items():
        ask(config["iam"], key, meta["label"])

    print("\n--- Zero Trust Posture ---")
    for key, meta in ZT_RUBRIC.items():
        ask(config["zero_trust"], key, meta["label"])

    print("\n--- PQC Readiness ---")
    for key, meta in PQC_RUBRIC.items():
        ask(config["pqc"], key, meta["label"])

    return config


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="IMM-CI Self-Assessment Tool -- companion to SmartNets 2026 paper"
    )
    parser.add_argument("--config", type=str, help="Path to YAML config file")
    parser.add_argument("--interactive", action="store_true", help="Run interactive questionnaire")
    parser.add_argument("--json-out", type=str, help="Write JSON result to file")
    args = parser.parse_args()

    if args.interactive:
        config = interactive_mode()
    elif args.config:
        if not YAML_AVAILABLE:
            print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        parser.print_help()
        sys.exit(0)

    result = run_assessment(config)
    print_report(result)

    if args.json_out:
        out_path = Path(args.json_out)
        with open(out_path, "w") as f:
            json.dump(asdict(result), f, indent=2)
        print(f"JSON report written to: {out_path}")


if __name__ == "__main__":
    main()
