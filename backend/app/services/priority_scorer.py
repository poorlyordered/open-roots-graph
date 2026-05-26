from datetime import datetime

from app.models.research_priority import ResearchPriorityItem, ResearchPrioritySummary

# Individuals born after this year may still be alive — exclude death/burial from completeness
ALIVE_CUTOFF = datetime.now().year - 95

# Completeness fields and their checks
COMPLETENESS_FIELDS = [
    ("birth_date", lambda d: d.get("birth_date_raw") is not None),
    ("birth_place", lambda d: d.get("has_birth_place", False)),
    ("death_date", lambda d: d.get("death_date_raw") is not None),
    ("death_place", lambda d: d.get("has_death_place", False)),
    ("burial_place", lambda d: d.get("has_burial_place", False)),
    ("parents", lambda d: d.get("has_parents", False)),
    ("sources", lambda d: (d.get("source_count") or 0) > 0),
]

DEATH_FIELDS = {"death_date", "death_place", "burial_place"}

# Researcher confidence by generation
# How certain you are that this person's data is correct
CONFIDENCE_LEVELS = {
    0: ("verified", 1.0),    # You — personally known
    1: ("verified", 1.0),    # Parents — personally known
    2: ("high", 0.85),       # Grandparents — living memory, family stories
    3: ("medium", 0.65),     # Great-grandparents — documented, some oral history
    4: ("medium", 0.50),     # 2x great — documented records
    5: ("low", 0.35),        # 3x great — records only
}
# Gen 6+ defaults to ("low", max(0.15, 0.35 - 0.05 * (gen - 5)))

# Priority weights (sum to 100)
W_GENERATION = 30
W_INCOMPLETENESS = 25
W_BRICK_WALL = 10
W_DIRECT_LINE = 10
W_CONFLICTS = 5
W_KEYSTONE = 20  # Bonus for individuals whose identification unlocks new branches


def _confidence_for_generation(gen: int) -> tuple[str, float]:
    if gen in CONFIDENCE_LEVELS:
        return CONFIDENCE_LEVELS[gen]
    # Decay for deeper generations
    conf = max(0.10, 0.35 - 0.05 * (gen - 5))
    return ("low", round(conf, 2))


class PriorityScorer:

    def score(
        self,
        completeness_data: list[dict],
        generation_map: dict[str, int],
        collateral_map: dict[str, dict],
    ) -> tuple[list[ResearchPriorityItem], ResearchPrioritySummary]:
        items = []

        # Build a lookup for counting how many direct-line descendants flow through each person
        # A brick wall at a high generation blocks more potential ancestors
        # Each generation doubles the potential ancestors (2 parents, 4 grandparents, etc.)
        # Keystone score = how many "slots" are blocked by this person having no parents
        brick_wall_ids = set()

        # First pass: identify brick walls and compute base data
        scored_data = []
        for row in completeness_data:
            indi_id = row["id"]
            generation = generation_map.get(indi_id, 0)
            is_direct = indi_id in generation_map
            relationship = "direct" if is_direct else "collateral"

            if not is_direct and indi_id in collateral_map:
                related_id = collateral_map[indi_id]["related_to"]
                generation = generation_map.get(related_id, 0)

            has_parents = row.get("has_parents", False)
            is_brick_wall = not has_parents and generation >= 1

            if is_brick_wall and is_direct:
                brick_wall_ids.add(indi_id)

            scored_data.append({
                "row": row,
                "generation": generation,
                "is_direct": is_direct,
                "relationship": relationship,
                "is_brick_wall": is_brick_wall,
            })

        # Second pass: compute scores
        for entry in scored_data:
            row = entry["row"]
            indi_id = row["id"]
            generation = entry["generation"]
            is_direct = entry["is_direct"]
            relationship = entry["relationship"]
            is_brick_wall = entry["is_brick_wall"]

            birth_year = row.get("birth_year")
            possibly_alive = birth_year is not None and birth_year > ALIVE_CUTOFF

            # Completeness
            applicable_fields = []
            missing = []
            for field_name, check_fn in COMPLETENESS_FIELDS:
                if possibly_alive and field_name in DEATH_FIELDS:
                    continue
                applicable_fields.append(field_name)
                if not check_fn(row):
                    missing.append(field_name)

            total_fields = len(applicable_fields)
            filled = total_fields - len(missing)
            completeness = filled / total_fields if total_fields > 0 else 0.0

            conflict_count = row.get("conflict_count", 0) or 0
            source_count = row.get("source_count", 0) or 0

            # Researcher confidence
            confidence_label, confidence_value = _confidence_for_generation(generation)

            # Keystone score: brick walls on the direct line at higher generations
            # block more potential ancestors (each generation doubles)
            # A gen-5 brick wall blocks 2^5 = 32 potential ancestors above them
            keystone_score = 0.0
            if is_brick_wall and is_direct:
                # Potential ancestors blocked = how many generations remain
                # More valuable the further back they are
                remaining_potential = min(2 ** min(generation, 8), 256)
                keystone_score = min(remaining_potential / 64, 1.0) * W_KEYSTONE

            # Priority score components
            gen_score = min(generation / 10, 1.0) * W_GENERATION
            incomp_score = (1.0 - completeness) * W_INCOMPLETENESS
            brick_score = W_BRICK_WALL if is_brick_wall else 0
            direct_score = W_DIRECT_LINE if is_direct else 0
            conflict_score = min(conflict_count / 3, 1.0) * W_CONFLICTS

            priority = (
                gen_score + incomp_score + direct_score
                + brick_score + conflict_score + keystone_score
            )

            items.append(ResearchPriorityItem(
                id=indi_id,
                name=row.get("name", "Unknown"),
                surname=row.get("surname"),
                sex=row.get("sex"),
                birth_year=birth_year,
                death_year=row.get("death_year"),
                generation=generation,
                relationship=relationship,
                completeness_score=round(completeness, 3),
                priority_score=round(priority, 1),
                missing_fields=missing,
                has_conflicts=conflict_count > 0,
                conflict_count=conflict_count,
                source_count=source_count,
                is_brick_wall=is_brick_wall,
                confidence_label=confidence_label,
                confidence_value=round(confidence_value, 2),
                keystone_score=round(keystone_score, 1),
            ))

        # Sort by priority descending
        items.sort(key=lambda x: x.priority_score, reverse=True)

        # Summary
        direct_items = [i for i in items if i.relationship == "direct"]
        collateral_items = [i for i in items if i.relationship == "collateral"]
        avg_comp = (
            sum(i.completeness_score for i in items) / len(items) if items else 0.0
        )

        summary = ResearchPrioritySummary(
            total_scored=len(items),
            brick_walls=sum(1 for i in items if i.is_brick_wall),
            avg_completeness=round(avg_comp, 3),
            direct_line_count=len(direct_items),
            collateral_count=len(collateral_items),
        )

        return items, summary
