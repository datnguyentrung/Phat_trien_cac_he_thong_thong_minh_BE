from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.medication.models import GraphContext

_CONSULTATION_QUERY = """
MATCH (d:Disease)
WHERE coalesce(d.is_active, false)
  AND (
    toLower(d.code) = $term
    OR toLower(d.name) = $term
    OR any(alias IN coalesce(d.aliases, []) WHERE toLower(alias) = $term)
    OR toLower(coalesce(d.search_keyword, '')) CONTAINS $term
    OR toLower(d.name) CONTAINS $term
    OR any(alias IN coalesce(d.aliases, []) WHERE toLower(alias) CONTAINS $term)
    OR $term CONTAINS toLower(d.name)
  )
WITH d,
  CASE
    WHEN toLower(d.code) = $term OR toLower(d.name) = $term THEN 0
    WHEN any(alias IN coalesce(d.aliases, []) WHERE toLower(alias) = $term) THEN 1
    ELSE 2
  END AS match_rank
ORDER BY match_rank, d.name
LIMIT 1
RETURN d {
  .node_id, .code, .name, .aliases, .description, .source_name, .source_url
} AS disease,
[(d)-[rel:HAS_CONSULTATION_NEED]->(need:ConsultationNeed)
  WHERE coalesce(rel.is_active, false) AND coalesce(need.is_active, false) |
  need {
    .node_id, .code, .name, .description, .long_chau_category_hints,
    .long_chau_category_slugs, priority: rel.priority,
    rationale: rel.rationale, evidence: rel.evidence,
    confidence: rel.confidence, condition_note: rel.condition_note,
    source_name: need.source_name, source_url: need.source_url
  }
] AS consultation_needs,
[(d)-[rel:HAS_WARNING]->(warning:Warning)
  WHERE coalesce(rel.is_active, false) AND coalesce(warning.is_active, false) |
  warning {
    .node_id, .code, .title, .message, .warning_type, .severity,
    .action_text, priority: rel.priority, rationale: rel.rationale,
    evidence: rel.evidence, confidence: rel.confidence,
    trigger_note: rel.trigger_note, source_name: warning.source_name,
    source_url: warning.source_url
  }
] AS warnings
"""


def _priority(item: dict[str, Any]) -> int:
    value = item.get("priority")
    return value if isinstance(value, int) else 100


_SEVERITY_RANK = {
    "CRITICAL": 0,
    "IMPORTANT": 1,
    "CAUTION": 2,
    "INFO": 3,
}


def _warning_order(item: dict[str, Any]) -> tuple[int, int]:
    severity = str(item.get("severity") or "").upper()
    return _SEVERITY_RANK.get(severity, 4), _priority(item)


def _sources(*groups: Any) -> list[dict[str, str]]:
    found: dict[tuple[str, str], dict[str, str]] = {}
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("source_name") or "").strip()
            url = str(item.get("source_url") or "").strip()
            if name or url:
                found[(name, url)] = {"name": name, "url": url}
    return list(found.values())


class Neo4jMedicationRepository:
    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    @classmethod
    def create(
        cls,
        uri: str,
        username: str,
        password: str,
        database: str,
    ) -> "Neo4jMedicationRepository":
        driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        return cls(driver=driver, database=database)

    async def find_consultation_context(
        self,
        condition: str,
    ) -> GraphContext | None:
        term = condition.strip().casefold()[:200]
        if not term:
            return None

        records, _, _ = await self._driver.execute_query(
            _CONSULTATION_QUERY,
            term=term,
            database_=self._database,
            routing_="r",
        )
        if not records:
            return None

        data = records[0].data()
        disease = data.get("disease")
        needs = sorted(data.get("consultation_needs") or [], key=_priority)
        warnings = sorted(data.get("warnings") or [], key=_warning_order)
        return GraphContext(
            disease=disease,
            consultation_needs=needs,
            warnings=warnings,
            sources=_sources(disease, needs, warnings),
        )

    async def close(self) -> None:
        await self._driver.close()
