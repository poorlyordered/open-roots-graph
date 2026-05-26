from __future__ import annotations

from dataclasses import asdict, dataclass, field as dataclass_field
from typing import Any, Literal

Severity = Literal["critical", "high", "medium", "low"]
FixMode = Literal["automatic", "review"]


@dataclass(frozen=True)
class FixProposal:
    field: str
    before: Any
    after: Any
    mode: FixMode
    confidence: float
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualityFinding:
    check_id: str
    severity: Severity
    entity_type: str
    entity_id: str
    message: str
    field: str | None = None
    observed: Any = None
    related_entity_ids: list[str] = dataclass_field(default_factory=list)
    suggested_action: str = ""
    confidence: float = 1.0
    fix: FixProposal | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.fix is None:
            data["fix"] = None
        return data


@dataclass(frozen=True)
class QualityReport:
    findings: list[QualityFinding]

    @property
    def summary(self) -> dict[str, Any]:
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_check: dict[str, int] = {}
        automatic_fixes = 0
        review_fixes = 0

        for finding in self.findings:
            by_severity[finding.severity] += 1
            by_check[finding.check_id] = by_check.get(finding.check_id, 0) + 1
            if finding.fix:
                if finding.fix.mode == "automatic":
                    automatic_fixes += 1
                else:
                    review_fixes += 1

        return {
            "total_findings": len(self.findings),
            "by_severity": by_severity,
            "by_check": dict(sorted(by_check.items())),
            "automatic_fixes": automatic_fixes,
            "review_fixes": review_fixes,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
        }
