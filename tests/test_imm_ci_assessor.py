"""
Unit and integration tests for imm_ci_assessor.py
IMM-CI Self-Assessment Tool — SmartNets 2026 companion artifact

Run: python -m pytest tests/test_imm_ci_assessor.py -v
"""

import sys
import json
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from imm_ci_assessor import (
    score_dimension,
    compute_composite_level,
    detect_stall,
    run_assessment,
    generate_summary,
    IAM_RUBRIC,
    ZT_RUBRIC,
    PQC_RUBRIC,
    DimensionScore,
)


# ---------------------------------------------------------------------------
# Fixtures: named profiles derived from IMM-CI Table II
# ---------------------------------------------------------------------------

def _all_false(rubric: dict) -> dict:
    return {k: False for k in rubric}

def _all_positive(rubric: dict) -> dict:
    return {k: (v["weight"] > 0) for k, v in rubric.items()}


LEVEL_1_CONFIG = {
    "organization": "Test Org L1",
    "iam": {**_all_false(IAM_RUBRIC), "password_only": True},
    "zero_trust": {**_all_false(ZT_RUBRIC), "perimeter_only": True},
    "pqc": {**_all_false(PQC_RUBRIC), "classical_only": True},
}

LEVEL_2_CONFIG = {
    "organization": "Test Org L2",
    "iam": {**_all_false(IAM_RUBRIC), "mfa_enforced": True,
            "ldap_ad_integration": True, "partial_abac": True},
    "zero_trust": {**_all_false(ZT_RUBRIC), "network_segmentation": True,
                   "some_zt_policies": True},
    "pqc": {**_all_false(PQC_RUBRIC), "crypto_inventory": True},
}

LAKESHORE_BASELINE = {
    "organization": "Lakeshore MWA Baseline",
    "iam": {
        "password_only": False, "mfa_enforced": True, "ldap_ad_integration": True,
        "partial_abac": True, "fido2_deployed": False, "scim_provisioning": False,
        "itdr_deployed": False, "spiffe_spire": False, "dids_piloted": False,
        "full_ssi": False, "autonomous_jml": False,
    },
    "zero_trust": {
        "perimeter_only": False, "network_segmentation": True, "some_zt_policies": True,
        "identity_control_plane": False, "caep_risc_active": False,
        "continuous_evaluation": False, "behavioral_analytics": False,
        "full_zta": False, "crypto_attestation_all": False,
    },
    "pqc": {
        "classical_only": False, "crypto_inventory": True, "migration_plan": False,
        "hybrid_pqc_test": False, "mlkem_mldsa_production": False,
        "crypto_agility_achieved": False,
    },
}

LAKESHORE_POST_PILOT = {
    "organization": "Lakeshore MWA Post-Pilot (Level 3 Target)",
    "iam": {
        "password_only": False, "mfa_enforced": True, "ldap_ad_integration": True,
        "partial_abac": True, "fido2_deployed": True, "scim_provisioning": True,
        "itdr_deployed": True, "spiffe_spire": False, "dids_piloted": False,
        "full_ssi": False, "autonomous_jml": False,
    },
    "zero_trust": {
        "perimeter_only": False, "network_segmentation": True, "some_zt_policies": True,
        "identity_control_plane": True, "caep_risc_active": True,
        "continuous_evaluation": False, "behavioral_analytics": False,
        "full_zta": False, "crypto_attestation_all": False,
    },
    "pqc": {
        "classical_only": False, "crypto_inventory": True, "migration_plan": True,
        "hybrid_pqc_test": True, "mlkem_mldsa_production": False,
        "crypto_agility_achieved": False,
    },
}


# ---------------------------------------------------------------------------
# Dimension scoring tests
# ---------------------------------------------------------------------------

class TestDimensionScoring:

    def test_empty_iam_does_not_crash(self):
        score = score_dimension("IAM", _all_false(IAM_RUBRIC), IAM_RUBRIC)
        assert isinstance(score.raw_score, float)
        assert 1 <= score.level <= 5

    def test_all_positive_iam_reaches_level5(self):
        score = score_dimension("IAM", _all_positive(IAM_RUBRIC), IAM_RUBRIC)
        assert score.level == 5, f"Expected level 5, got {score.level}"

    def test_password_only_penalizes_score(self):
        # Give each org MFA so there are positive contributions to differentiate.
        # password_only=True should still score lower than password_only=False.
        base_with_mfa = {**_all_false(IAM_RUBRIC), "mfa_enforced": True}
        penalized = {**base_with_mfa, "password_only": True}
        clean = {**base_with_mfa, "password_only": False}
        s_pen = score_dimension("IAM Capabilities", penalized, IAM_RUBRIC)
        s_clean = score_dimension("IAM Capabilities", clean, IAM_RUBRIC)
        assert s_pen.raw_score < s_clean.raw_score

    def test_score_clamped_0_to_100(self):
        worst = {k: True for k in IAM_RUBRIC if IAM_RUBRIC[k]["weight"] < 0}
        worst.update({k: False for k in IAM_RUBRIC if IAM_RUBRIC[k]["weight"] > 0})
        score = score_dimension("IAM", worst, IAM_RUBRIC)
        assert 0 <= score.raw_score <= 100

    def test_gaps_populated_for_missing_capabilities(self):
        score = score_dimension("IAM", _all_false(IAM_RUBRIC), IAM_RUBRIC)
        assert len(score.gaps) > 0

    def test_next_steps_not_exceed_5(self):
        score = score_dimension("IAM", _all_false(IAM_RUBRIC), IAM_RUBRIC)
        assert len(score.next_steps) <= 5


class TestCompositeLevel:

    def test_composite_is_minimum_of_three(self):
        iam = DimensionScore("IAM", 75.0, 4, [], [])
        zt = DimensionScore("ZT", 55.0, 3, [], [])
        pqc = DimensionScore("PQC", 25.0, 2, [], [])
        assert compute_composite_level(iam, zt, pqc) == 2

    def test_all_level5_gives_5(self):
        d = DimensionScore("x", 90.0, 5, [], [])
        assert compute_composite_level(d, d, d) == 5

    def test_weakest_link_principle(self):
        high = DimensionScore("x", 90.0, 5, [], [])
        low = DimensionScore("x", 10.0, 1, [], [])
        assert compute_composite_level(high, high, low) == 1


class TestStallDetection:

    def test_l2_stall_detected(self):
        iam = DimensionScore("IAM", 35.0, 2, [], [])
        zt = DimensionScore("ZT", 45.0, 3, [], [])
        pqc = DimensionScore("PQC", 25.0, 2, [], [])
        assert detect_stall(iam, zt, pqc) is True

    def test_no_stall_at_level3(self):
        iam = DimensionScore("IAM", 55.0, 3, [], [])
        zt = DimensionScore("ZT", 55.0, 3, [], [])
        pqc = DimensionScore("PQC", 35.0, 2, [], [])
        assert detect_stall(iam, zt, pqc) is False

    def test_no_stall_if_iam_above_2(self):
        iam = DimensionScore("IAM", 55.0, 3, [], [])
        zt = DimensionScore("ZT", 35.0, 2, [], [])
        pqc = DimensionScore("PQC", 15.0, 1, [], [])
        assert detect_stall(iam, zt, pqc) is False


# ---------------------------------------------------------------------------
# Integration tests: named profiles
# ---------------------------------------------------------------------------

class TestNamedProfiles:

    def test_level1_org_scores_level1(self):
        result = run_assessment(LEVEL_1_CONFIG)
        assert result.composite_level == 1

    def test_level2_org_scores_level2(self):
        result = run_assessment(LEVEL_2_CONFIG)
        assert result.composite_level == 2

    def test_lakeshore_baseline_is_level2(self):
        result = run_assessment(LAKESHORE_BASELINE)
        assert result.composite_level == 2, (
            f"Expected Lakeshore baseline at L2, got {result.composite_level}"
        )

    def test_lakeshore_baseline_triggers_stall_warning(self):
        result = run_assessment(LAKESHORE_BASELINE)
        assert result.stall_warning is True

    def test_lakeshore_post_pilot_reaches_level3(self):
        result = run_assessment(LAKESHORE_POST_PILOT)
        assert result.composite_level == 3, (
            f"Expected post-pilot at L3, got {result.composite_level}"
        )

    def test_lakeshore_post_pilot_clears_stall_warning(self):
        result = run_assessment(LAKESHORE_POST_PILOT)
        assert result.stall_warning is False

    def test_priority_actions_populated(self):
        result = run_assessment(LAKESHORE_BASELINE)
        assert len(result.priority_actions) > 0

    def test_executive_summary_contains_org_name(self):
        result = run_assessment(LAKESHORE_BASELINE)
        assert "Lakeshore" in result.executive_summary

    def test_executive_summary_contains_level(self):
        result = run_assessment(LAKESHORE_BASELINE)
        assert "Level" in result.executive_summary


# ---------------------------------------------------------------------------
# JSON output test
# ---------------------------------------------------------------------------

class TestJsonOutput:

    def test_result_is_json_serializable(self):
        from dataclasses import asdict
        result = run_assessment(LAKESHORE_BASELINE)
        serialized = json.dumps(asdict(result))
        loaded = json.loads(serialized)
        assert loaded["composite_level"] == result.composite_level
        assert loaded["org_name"] == result.org_name

    def test_json_contains_all_dimensions(self):
        from dataclasses import asdict
        result = run_assessment(LAKESHORE_BASELINE)
        d = asdict(result)
        assert "iam_score" in d
        assert "zt_score" in d
        assert "pqc_score" in d


# ---------------------------------------------------------------------------
# Regression: pilot improvement shows measurable delta
# ---------------------------------------------------------------------------

class TestPilotDelta:

    def test_pilot_improves_iam_score(self):
        baseline = run_assessment(LAKESHORE_BASELINE)
        post = run_assessment(LAKESHORE_POST_PILOT)
        assert post.iam_score.raw_score > baseline.iam_score.raw_score

    def test_pilot_improves_zt_score(self):
        baseline = run_assessment(LAKESHORE_BASELINE)
        post = run_assessment(LAKESHORE_POST_PILOT)
        assert post.zt_score.raw_score > baseline.zt_score.raw_score

    def test_pilot_improves_pqc_score(self):
        baseline = run_assessment(LAKESHORE_BASELINE)
        post = run_assessment(LAKESHORE_POST_PILOT)
        assert post.pqc_score.raw_score > baseline.pqc_score.raw_score

    def test_pilot_composite_level_advances(self):
        baseline = run_assessment(LAKESHORE_BASELINE)
        post = run_assessment(LAKESHORE_POST_PILOT)
        assert post.composite_level > baseline.composite_level
