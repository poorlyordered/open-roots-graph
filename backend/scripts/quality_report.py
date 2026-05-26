"""Run reusable GEDCOM quality checks and write a JSON report.

Usage:
    python -m scripts.quality_report
    python -m scripts.quality_report --gedcom ../examples/sample-tree.ged --out ../data/quality_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.quality_engine import GedcomQualityRunner
from scripts.import_tree import parse_gedcom

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run GEDCOM data quality checks.")
    parser.add_argument(
        "--gedcom",
        default=os.getenv("GEDCOM_PATH", str(ROOT / "examples" / "sample-tree.ged")),
        help="Path to a GEDCOM file. Defaults to GEDCOM_PATH or examples/sample-tree.ged.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "quality_report.json"),
        help="Output JSON report path.",
    )
    args = parser.parse_args()

    gedcom_path = Path(args.gedcom)
    if not gedcom_path.is_absolute():
        cwd_path = Path.cwd() / gedcom_path
        gedcom_path = cwd_path if cwd_path.exists() else ROOT / gedcom_path

    individuals, families, _sources = parse_gedcom(gedcom_path)
    report = GedcomQualityRunner().run(individuals, families)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2, default=str) + "\n", encoding="utf-8")

    summary = report.summary
    print(f"Wrote {out_path}")
    print(f"Findings: {summary['total_findings']}")
    print(f"By severity: {summary['by_severity']}")
    print(f"Automatic fixes: {summary['automatic_fixes']}")
    print(f"Review fixes: {summary['review_fixes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
