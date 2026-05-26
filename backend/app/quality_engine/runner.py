from __future__ import annotations

from app.quality_engine.checks import check_families, check_people
from app.quality_engine.models import QualityFinding, QualityReport


class GedcomQualityRunner:
    """Run reusable quality checks over parsed GEDCOM dictionaries."""

    def run(self, individuals: dict[str, dict], families: dict[str, dict]) -> QualityReport:
        findings: list[QualityFinding] = []
        findings.extend(check_people(individuals))
        findings.extend(check_families(individuals, families))
        findings.sort(key=_sort_key)
        return QualityReport(findings=findings)


def _sort_key(finding: QualityFinding) -> tuple[int, str, str]:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return (severity_order[finding.severity], finding.check_id, finding.entity_id)

