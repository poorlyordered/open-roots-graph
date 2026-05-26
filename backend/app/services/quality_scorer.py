from app.models.quality import QualityScoreItem, QualitySummary
from app.services.priority_scorer import COMPLETENESS_FIELDS, DEATH_FIELDS, ALIVE_CUTOFF

# Global priority weights (no generation/keystone since those need a root)
# Score 0-100: higher = more urgent to research
W_INCOMPLETENESS = 40   # Missing fields (biggest factor)
W_BRICK_WALL = 20       # No known parents
W_UNSOURCED = 20        # No source citations
W_CONFLICTS = 10        # Has conflicting claims
W_NO_DATES = 10         # Missing both birth and death years


class QualityScorer:

    def score_all(
        self, completeness_data: list[dict]
    ) -> tuple[list[QualityScoreItem], QualitySummary]:
        items: list[QualityScoreItem] = []
        field_totals: dict[str, int] = {}
        field_filled: dict[str, int] = {}

        for row in completeness_data:
            birth_year = row.get("birth_year")
            death_year = row.get("death_year")
            possibly_alive = birth_year is not None and birth_year > ALIVE_CUTOFF

            applicable_fields: list[str] = []
            missing: list[str] = []

            for field_name, check_fn in COMPLETENESS_FIELDS:
                if possibly_alive and field_name in DEATH_FIELDS:
                    continue
                applicable_fields.append(field_name)
                field_totals[field_name] = field_totals.get(field_name, 0) + 1
                if check_fn(row):
                    field_filled[field_name] = field_filled.get(field_name, 0) + 1
                else:
                    missing.append(field_name)

            total_fields = len(applicable_fields)
            filled = total_fields - len(missing)
            completeness = (filled / total_fields * 100) if total_fields > 0 else 0.0

            source_count = row.get("source_count", 0) or 0
            conflict_count = row.get("conflict_count", 0) or 0
            has_parents = row.get("has_parents", False)
            is_brick_wall = not has_parents

            # Priority score: higher = needs more work
            incomp_score = (1.0 - completeness / 100) * W_INCOMPLETENESS
            brick_score = W_BRICK_WALL if is_brick_wall else 0
            unsourced_score = W_UNSOURCED if source_count == 0 else 0
            conflict_score = min(conflict_count / 3, 1.0) * W_CONFLICTS
            date_score = W_NO_DATES if (birth_year is None and death_year is None) else 0

            priority = incomp_score + brick_score + unsourced_score + conflict_score + date_score

            items.append(QualityScoreItem(
                id=row.get("id", ""),
                name=row.get("name", "Unknown"),
                surname=row.get("surname"),
                sex=row.get("sex"),
                birth_year=birth_year,
                death_year=death_year,
                completeness_pct=round(completeness, 1),
                missing_fields=missing,
                missing_count=len(missing),
                source_count=source_count,
                conflict_count=conflict_count,
                priority_score=round(priority, 1),
                is_brick_wall=is_brick_wall,
            ))

        # Summary
        total = len(items)
        avg = sum(i.completeness_pct for i in items) / total if total else 0.0

        completeness_by_field: dict[str, float] = {}
        for field_name in field_totals:
            t = field_totals[field_name]
            f = field_filled.get(field_name, 0)
            completeness_by_field[field_name] = round(f / t * 100, 1) if t else 0.0

        summary = QualitySummary(
            total_individuals=total,
            avg_completeness=round(avg, 1),
            fully_complete=sum(1 for i in items if i.completeness_pct >= 100.0),
            unsourced_count=sum(1 for i in items if i.source_count == 0),
            quick_win_count=sum(1 for i in items if i.missing_count == 1),
            completeness_by_field=completeness_by_field,
        )

        return items, summary
