"""
Benchmark runner — generates results/benchmark_results.json
Runs all config profiles through the IMM-CI assessor and produces a
comparative JSON artifact suitable for academic citation and GRC tooling.

Run: python generate_benchmark_results.py
"""

import json
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone

import yaml
from imm_ci_assessor import run_assessment

CONFIGS = [
    ("config/energy_sector_level1.yaml",    "Energy Sector — Level 1 Baseline"),
    ("config/sample_org.yaml",              "Water/Wastewater — Level 2 Baseline (Lakeshore MWA)"),
    ("config/healthcare_level2.yaml",       "Healthcare CI — Level 2"),
    ("config/water_level3_post_pilot.yaml", "Water/Wastewater — Level 3 Post-Pilot (Lakeshore MWA)"),
    ("config/financial_level4.yaml",        "Financial Services CI — Level 4"),
]

OUT = Path("results/benchmark_results.json")
OUT.parent.mkdir(exist_ok=True)


def main():
    benchmark = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "tool_version": "1.0.0",
        "paper": "The Metamorphosis of Access: Strategic Imperatives for Identity 3.0 "
                 "and Zero Trust Integration in Critical Infrastructure",
        "conference": "SmartNets 2026 CyberSec CIIA",
        "authors": ["Sunil Gentyala", "Floriano Caprio"],
        "profiles": []
    }

    print(f"\n{'='*60}")
    print(f"  IMM-CI Benchmark Run — {benchmark['generated'][:10]}")
    print(f"{'='*60}\n")

    for config_path, label in CONFIGS:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        result = run_assessment(config)
        d = asdict(result)

        row = {
            "profile_label": label,
            "config_file": config_path,
            "composite_level": result.composite_level,
            "iam_level": result.iam_score.level,
            "iam_score": result.iam_score.raw_score,
            "zt_level": result.zt_score.level,
            "zt_score": result.zt_score.raw_score,
            "pqc_level": result.pqc_score.level,
            "pqc_score": result.pqc_score.raw_score,
            "stall_warning": result.stall_warning,
            "executive_summary": result.executive_summary,
            "top_priority_actions": result.priority_actions[:3],
        }
        benchmark["profiles"].append(row)

        lvl_bar = "=" * (result.composite_level * 10)
        print(f"  {label}")
        print(f"  Composite: L{result.composite_level}  [{lvl_bar}{'.'*(50 - result.composite_level*10)}]")
        print(f"  IAM L{result.iam_score.level} ({result.iam_score.raw_score:.1f})  |  "
              f"ZT L{result.zt_score.level} ({result.zt_score.raw_score:.1f})  |  "
              f"PQC L{result.pqc_score.level} ({result.pqc_score.raw_score:.1f})")
        if result.stall_warning:
            print(f"  *** L2->L3 stall pattern detected ***")
        print()

    with open(OUT, "w") as f:
        json.dump(benchmark, f, indent=2)

    print(f"{'='*60}")
    print(f"  Benchmark complete. {len(CONFIGS)} profiles assessed.")
    print(f"  Results written to: {OUT}")
    print(f"{'='*60}\n")

    # Print cross-sector comparison table
    print("  CROSS-SECTOR IMM-CI LEVEL COMPARISON")
    print(f"  {'Sector':<42} {'L-IAM':>5} {'L-ZT':>5} {'L-PQC':>6} {'Composite':>10}")
    print(f"  {'-'*70}")
    for p in benchmark["profiles"]:
        name = p["profile_label"][:41]
        print(f"  {name:<42} {p['iam_level']:>5} {p['zt_level']:>5} "
              f"{p['pqc_level']:>6} {p['composite_level']:>10}")
    print()


if __name__ == "__main__":
    main()
