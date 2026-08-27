from typing import Any

import pytest

from app.medication.neo4j_repository import Neo4jMedicationRepository


class FakeRecord:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def data(self) -> dict[str, Any]:
        return self._data


class FakeDriver:
    def __init__(self, records: list[FakeRecord]) -> None:
        self.records = records
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute_query(self, query: str, **parameters: Any):
        self.calls.append((query, parameters))
        return self.records, None, None

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_repository_uses_parameterized_read_query_and_explicit_database() -> None:
    condition = "đau đầu' MATCH (n) DETACH DELETE n //"
    driver = FakeDriver([])
    repository = Neo4jMedicationRepository(driver=driver, database="medication")

    result = await repository.find_consultation_context(condition)

    assert result is None
    query, parameters = driver.calls[0]
    assert condition not in query
    assert parameters["term"] == condition.casefold()
    assert parameters["database_"] == "medication"
    assert parameters["routing_"] == "r"
    assert "coalesce(d.is_active, false)" in query
    assert "coalesce(rel.is_active, false)" in query


@pytest.mark.asyncio
async def test_repository_orders_warnings_by_severity_then_priority() -> None:
    warnings = [
        {
            "title": "Caution",
            "message": "Caution message",
            "severity": "CAUTION",
            "priority": 1,
        },
        {
            "title": "Critical later",
            "message": "Critical later message",
            "severity": "CRITICAL",
            "priority": 9,
        },
        {
            "title": "Critical first",
            "message": "Critical first message",
            "severity": "CRITICAL",
            "priority": 2,
        },
    ]
    driver = FakeDriver(
        [
            FakeRecord(
                {
                    "disease": {"name": "Đau đầu"},
                    "consultation_needs": [],
                    "warnings": warnings,
                }
            )
        ]
    )
    repository = Neo4jMedicationRepository(driver=driver, database="neo4j")

    result = await repository.find_consultation_context("đau đầu")

    assert result is not None
    assert [warning.title for warning in result.warnings] == [
        "Critical first",
        "Critical later",
        "Caution",
    ]
