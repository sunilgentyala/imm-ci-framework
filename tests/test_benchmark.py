"""
Benchmark integration tests — validates all sector profiles produce
expected IMM-CI levels and that cross-sector ordering is correct.
"""

import json
import sys
from pathlib import Path
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from imm_ci_assessor import run_assessment


def load(config_path: str) -> dict:
    with open(Path(__file__).parent.parent / config_path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Per-profile level assertions
# ---------------------------------------------------------------------------

class TestSectorProfiles:

    def test_energy_level1_baseline(self):
        result = run_assessment(load("config/energy_sector_level1.yaml"))
        assert result.composite_level == 1, f"Expected L1, got L{result.composite_level}"

    def test_water_level2_baseline(self):
        result = run_assessment(load("config/sample_org.yaml"))
        assert result.composite_level == 2

    def test_healthcare_level2(self):
        result = run_assessment(load("config/healthcare_level2.yaml"))
        assert result.composite_level == 2

    def test_water_level3_post_pilot(self):
        result = run_assessment(load("config/water_level3_post_pilot.yaml"))
        assert result.composite_level == 3, f"Expected L3, got L{result.composite_level}"

    def test_financial_level4(self):
        result = run_assessment(load("config/financial_level4.yaml"))
        assert result.composite_level == 4, f"Expected L4, got L{result.composite_level}"


# ---------------------------------------------------------------------------
# Cross-sector ordering: scores must increase monotonically
# ---------------------------------------------------------------------------

class TestCrossSectorOrdering:

    @pytest.fixture(scope="class")
    def profiles(self):
        configs = [
            "config/energy_sector_level1.yaml",
            "config/sample_org.yaml",
            "config/water_level3_post_pilot.yaml",
            "config/financial_level4.yaml",
        ]
        return [run_assessment(load(c)) for c in configs]

    def test_composite_levels_are_monotonically_increasing(self, profiles):
        levels = [p.composite_level for p in profiles]
        assert levels == sorted(levels), f"Levels not monotonically increasing: {levels}"

    def test_iam_scores_increase_across_sectors(self, profiles):
        scores = [p.iam_score.raw_score for p in profiles]
        assert scores == sorted(scores), f"IAM scores not ordered: {scores}"

    def test_zt_scores_increase_across_sectors(self, profiles):
        scores = [p.zt_score.raw_score for p in profiles]
        assert scores == sorted(scores), f"ZT scores not ordered: {scores}"

    def test_pqc_scores_increase_across_sectors(self, profiles):
        scores = [p.pqc_score.raw_score for p in profiles]
        assert scores == sorted(scores), f"PQC scores not ordered: {scores}"


# ---------------------------------------------------------------------------
# Stall pattern: both Level 2 profiles should trigger it
# ---------------------------------------------------------------------------

class TestStallPatternAcrossSectors:

    def test_water_l2_stall(self):
        result = run_assessment(load("config/sample_org.yaml"))
        assert result.stall_warning is True

    def test_healthcare_l2_stall(self):
        result = run_assessment(load("config/healthcare_level2.yaml"))
        assert result.stall_warning is True

    def test_level1_no_stall(self):
        result = run_assessment(load("config/energy_sector_level1.yaml"))
        assert result.stall_warning is False

    def test_level3_no_stall(self):
        result = run_assessment(load("config/water_level3_post_pilot.yaml"))
        assert result.stall_warning is False

    def test_level4_no_stall(self):
        result = run_assessment(load("config/financial_level4.yaml"))
        assert result.stall_warning is False


# ---------------------------------------------------------------------------
# Benchmark JSON output validation
# ---------------------------------------------------------------------------

class TestBenchmarkOutput:

    @pytest.fixture(scope="class")
    def benchmark_json(self):
        path = Path(__file__).parent.parent / "results" / "benchmark_results.json"
        if not path.exists():
            pytest.skip("benchmark_results.json not generated yet — run generate_benchmark_results.py")
        with open(path) as f:
            return json.load(f)

    def test_benchmark_has_five_profiles(self, benchmark_json):
        assert len(benchmark_json["profiles"]) == 5

    def test_benchmark_composite_levels_correct(self, benchmark_json):
        expected = [1, 2, 2, 3, 4]
        actual = [p["composite_level"] for p in benchmark_json["profiles"]]
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_benchmark_stall_flags_correct(self, benchmark_json):
        expected_stalls = [False, True, True, False, False]
        actual = [p["stall_warning"] for p in benchmark_json["profiles"]]
        assert actual == expected_stalls

    def test_benchmark_has_metadata(self, benchmark_json):
        assert "generated" in benchmark_json
        assert "tool_version" in benchmark_json
        assert "paper" in benchmark_json
        assert benchmark_json["tool_version"] == "1.0.0"
