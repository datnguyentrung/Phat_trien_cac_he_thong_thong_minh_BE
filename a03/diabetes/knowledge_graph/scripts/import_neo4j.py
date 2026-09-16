from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from config.neo4j import Neo4jClient

ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "data" / "nodes"
RELS = ROOT / "data" / "relationships"

DATABASE = Neo4jClient.database_name
BATCH_SIZE = int(os.getenv("NEO4J_BATCH_SIZE", "5000"))

CONSTRAINTS = [
    "CREATE CONSTRAINT respondent_id_unique IF NOT EXISTS FOR (n:Respondent) REQUIRE n.respondent_id IS UNIQUE",
    "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (n:Concept) REQUIRE n.concept_id IS UNIQUE",
    "CREATE INDEX concept_feature_idx IF NOT EXISTS FOR (n:Concept) ON (n.feature)",
]

UPSERT_RESPONDENTS = """
UNWIND $rows AS row
MERGE (r:Respondent {respondent_id: row.respondent_id})
SET r.bmi = row.BMI,
    r.mental_health_days = row.MentHlth,
    r.physical_health_days = row.PhysHlth,
    r.general_health = row.GenHlth,
    r.age_group = row.AgeGroup,
    r.education = row.Education,
    r.income = row.Income
"""

UPSERT_CONCEPTS = """
UNWIND $rows AS row
MERGE (c:Concept {concept_id: row.concept_id})
SET c.feature = row.feature,
    c.category = row.category,
    c.name = row.name
"""

UPSERT_EDGES = """
UNWIND $rows AS row
MATCH (r:Respondent {respondent_id: row.respondent_id})
MATCH (c:Concept {concept_id: row.concept_id})
MERGE (r)-[e:HAS_INDICATOR {source_feature: row.source_feature}]->(c)
SET e.value = toInteger(row.value),
    e.relation = row.relation
"""


def normalize_value(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def iter_csv_batches(path: Path, batch_size: int):
    for chunk in pd.read_csv(path, chunksize=batch_size):
        yield [
            {k: normalize_value(v) for k, v in row.items()}
            for row in chunk.to_dict(orient="records")
        ]


def run_query(driver, query, rows=None):
    with driver.session(database=DATABASE) as session:
        if rows is None:
            session.run(query).consume()
        else:
            session.run(query, rows=rows).consume()


def import_file(driver, path: Path, query: str, label: str):
    count = 0
    for rows in iter_csv_batches(path, BATCH_SIZE):
        run_query(driver, query, rows)
        count += len(rows)
        print(f"{label}: {count:,}", end="\r")
    print(f"{label}: {count:,} imported")


def main():
    driver = Neo4jClient.get_driver()
    try:
        for query in CONSTRAINTS:
            run_query(driver, query)

        import_file(driver, NODES / "respondents.csv", UPSERT_RESPONDENTS, "Respondent nodes")
        import_file(driver, NODES / "concepts.csv", UPSERT_CONCEPTS, "Concept nodes")
        import_file(
            driver, RELS / "respondent_concepts.csv", UPSERT_EDGES, "Indicator relationships"
        )

        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (n) WITH count(n) AS nodes
                MATCH ()-[r]->() RETURN nodes, count(r) AS relationships
            """).single()
            print("\\n=== Diabetes KG Import Completed ===")
            print("nodes:", result["nodes"])
            print("relationships:", result["relationships"])
    finally:
        Neo4jClient.close_driver()


if __name__ == "__main__":
    main()
