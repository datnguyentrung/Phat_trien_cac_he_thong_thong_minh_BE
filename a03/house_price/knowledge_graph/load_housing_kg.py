from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pandas as pd

from config.neo4j import Neo4jClient

ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "data" / "nodes"
RELS = ROOT / "data" / "relationships"

DATABASE = Neo4jClient.database_name
BATCH_SIZE = int(os.getenv("NEO4J_BATCH_SIZE", "5000"))
REPLACE_HOUSING_KG = os.getenv("HOUSING_KG_REPLACE", "false").lower() in {
    "1",
    "true",
    "yes",
}

HOUSE_NODES = NODES / "housing_houses.csv"
DISTRICT_NODES = NODES / "housing_districts.csv"
CITY_NODES = NODES / "housing_cities.csv"

HOUSE_LOCATED_IN = RELS / "housing_house_located_in_district.csv"
DISTRICT_BELONGS_TO = RELS / "housing_district_belongs_to_city.csv"


CONSTRAINTS = [
    """
    CREATE CONSTRAINT housing_house_id IF NOT EXISTS
    FOR (n:HousingHouse)
    REQUIRE n.house_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT housing_district_id IF NOT EXISTS
    FOR (n:HousingDistrict)
    REQUIRE n.district_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT housing_city_id IF NOT EXISTS
    FOR (n:HousingCity)
    REQUIRE n.city_id IS UNIQUE
    """,
]


UPSERT_HOUSES = """
UNWIND $rows AS row
MERGE (h:HousingHouse:House:HousingKG {house_id: row.house_id})
SET h.detail_url = row.detail_url,
    h.title = row.title,
    h.location_raw = row.location_raw,
    h.timeline_hours = row.timeline_hours,
    h.area_m2 = row.area_m2,
    h.bedrooms = row.bedrooms,
    h.bathrooms = row.bathrooms,
    h.floors = row.floors,
    h.frontage = row.frontage,
    h.price_million_vnd = row.price_million_vnd,
    h.source_dataset = 'house_buying_dec29th_2025.csv'
"""


UPSERT_DISTRICTS = """
UNWIND $rows AS row
MERGE (d:HousingDistrict:District:HousingKG {district_id: row.district_id})
SET d.name = row.district_name,
    d.city_id = row.city_id,
    d.source_dataset = 'house_buying_dec29th_2025.csv'
"""


UPSERT_CITIES = """
UNWIND $rows AS row
MERGE (c:HousingCity:City:HousingKG {city_id: row.city_id})
SET c.name = row.city_name,
    c.source_dataset = 'house_buying_dec29th_2025.csv'
"""


UPSERT_HOUSE_LOCATED_IN = """
UNWIND $rows AS row
MATCH (h:HousingHouse {house_id: row.house_id})
MATCH (d:HousingDistrict {district_id: row.district_id})
MERGE (h)-[:LOCATED_IN]->(d)
"""


UPSERT_DISTRICT_BELONGS_TO = """
UNWIND $rows AS row
MATCH (d:HousingDistrict {district_id: row.district_id})
MATCH (c:HousingCity {city_id: row.city_id})
MERGE (d)-[:BELONGS_TO]->(c)
"""


def _clean_scalar(value):
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return bool(value)

    if hasattr(value, "item"):
        value = value.item()

    return value


def _iter_batches(path: Path, batch_size: int) -> Iterator[list[dict]]:
    for chunk in pd.read_csv(path, chunksize=batch_size):
        rows = []

        for record in chunk.to_dict(orient="records"):
            rows.append(
                {
                    key: _clean_scalar(value)
                    for key, value in record.items()
                }
            )

        yield rows


def _run_batched(session, query: str, path: Path) -> int:
    total = 0

    for rows in _iter_batches(path, BATCH_SIZE):
        session.run(query, rows=rows).consume()
        total += len(rows)
        print(f"  {path.name}: {total:,}")

    return total


def _open_session(driver):
    if DATABASE:
        return driver.session(database=DATABASE)
    return driver.session()


def main() -> None:
    required = [
        HOUSE_NODES,
        DISTRICT_NODES,
        CITY_NODES,
        HOUSE_LOCATED_IN,
        DISTRICT_BELONGS_TO,
    ]

    missing = [path for path in required if not path.exists()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Thiếu Housing KG CSV. Hãy chạy prepare_housing_kg.py trước:\n"
            + joined
        )

    driver = Neo4jClient.get_driver()

    try:
        with _open_session(driver) as session:
            if REPLACE_HOUSING_KG:
                print("Deleting existing HousingKG subgraph...")
                session.run(
                    "MATCH (n:HousingKG) DETACH DELETE n"
                ).consume()

            print("Creating constraints...")
            for query in CONSTRAINTS:
                session.run(query).consume()

            print("Loading cities...")
            _run_batched(session, UPSERT_CITIES, CITY_NODES)

            print("Loading districts...")
            _run_batched(session, UPSERT_DISTRICTS, DISTRICT_NODES)

            print("Loading houses...")
            _run_batched(session, UPSERT_HOUSES, HOUSE_NODES)

            print("Loading House-[:LOCATED_IN]->District...")
            _run_batched(
                session,
                UPSERT_HOUSE_LOCATED_IN,
                HOUSE_LOCATED_IN,
            )

            print("Loading District-[:BELONGS_TO]->City...")
            _run_batched(
                session,
                UPSERT_DISTRICT_BELONGS_TO,
                DISTRICT_BELONGS_TO,
            )

            print("\nVerification:")
            result = session.run(
                """
                MATCH (h:HousingHouse)
                OPTIONAL MATCH (h)-[:LOCATED_IN]->(d:HousingDistrict)
                OPTIONAL MATCH (d)-[:BELONGS_TO]->(c:HousingCity)
                RETURN
                    count(DISTINCT h) AS houses,
                    count(DISTINCT d) AS districts,
                    count(DISTINCT c) AS cities
                """
            ).single()

            print(dict(result) if result is not None else {})

        print("\nHousing KG load complete.")

    finally:
        Neo4jClient.close_driver()


if __name__ == "__main__":
    main()
