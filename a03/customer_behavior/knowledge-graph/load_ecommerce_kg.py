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
REPLACE_ECOMMERCE_KG = os.getenv(
    "ECOMMERCE_KG_REPLACE",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
}

REVIEW_NODES = NODES / "ecommerce_reviews.csv"
PRODUCT_NODES = NODES / "ecommerce_products.csv"
DEPARTMENT_NODES = NODES / "ecommerce_departments.csv"
CLASS_NODES = NODES / "ecommerce_classes.csv"
DIVISION_NODES = NODES / "ecommerce_divisions.csv"

REVIEW_REVIEWS_PRODUCT = RELS / "ecommerce_review_reviews_product.csv"
REVIEW_ABOUT_DEPARTMENT = RELS / "ecommerce_review_about_department.csv"
REVIEW_IN_CLASS = RELS / "ecommerce_review_in_class.csv"
REVIEW_IN_DIVISION = RELS / "ecommerce_review_in_division.csv"
CLASS_BELONGS_TO_DEPARTMENT = (
    RELS / "ecommerce_class_belongs_to_department.csv"
)


CONSTRAINTS = [
    """
    CREATE CONSTRAINT ecommerce_review_id IF NOT EXISTS
    FOR (n:EcommerceReview)
    REQUIRE n.review_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT ecommerce_product_id IF NOT EXISTS
    FOR (n:EcommerceProduct)
    REQUIRE n.product_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT ecommerce_department_id IF NOT EXISTS
    FOR (n:EcommerceDepartment)
    REQUIRE n.department_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT ecommerce_class_id IF NOT EXISTS
    FOR (n:EcommerceClass)
    REQUIRE n.class_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT ecommerce_division_id IF NOT EXISTS
    FOR (n:EcommerceDivision)
    REQUIRE n.division_id IS UNIQUE
    """,
]


UPSERT_REVIEWS = """
UNWIND $rows AS row
MERGE (r:EcommerceReview:Review:EcommerceKG {review_id: row.review_id})
SET r.source_row_id = row.source_row_id,
    r.age = row.age,
    r.title = row.title,
    r.review_text = row.review_text,
    r.combined_text = row.combined_text,
    r.rating = row.rating,
    r.recommended_ind = row.recommended_ind,
    r.positive_feedback_count = row.positive_feedback_count,
    r.source_dataset = 'Womens Clothing E-Commerce Reviews.csv'
"""


UPSERT_PRODUCTS = """
UNWIND $rows AS row
MERGE (p:EcommerceProduct:Product:EcommerceKG {product_id: row.product_id})
SET p.clothing_id = row.clothing_id,
    p.source_dataset = 'Womens Clothing E-Commerce Reviews.csv'
"""


UPSERT_DEPARTMENTS = """
UNWIND $rows AS row
MERGE (
    d:EcommerceDepartment:Department:EcommerceKG
    {department_id: row.department_id}
)
SET d.name = row.department_name,
    d.source_dataset = 'Womens Clothing E-Commerce Reviews.csv'
"""


UPSERT_CLASSES = """
UNWIND $rows AS row
MERGE (c:EcommerceClass:ProductClass:EcommerceKG {class_id: row.class_id})
SET c.name = row.class_name,
    c.source_dataset = 'Womens Clothing E-Commerce Reviews.csv'
"""


UPSERT_DIVISIONS = """
UNWIND $rows AS row
MERGE (
    d:EcommerceDivision:Division:EcommerceKG
    {division_id: row.division_id}
)
SET d.name = row.division_name,
    d.source_dataset = 'Womens Clothing E-Commerce Reviews.csv'
"""


UPSERT_REVIEW_REVIEWS_PRODUCT = """
UNWIND $rows AS row
MATCH (r:EcommerceReview {review_id: row.review_id})
MATCH (p:EcommerceProduct {product_id: row.product_id})
MERGE (r)-[:REVIEWS]->(p)
"""


UPSERT_REVIEW_ABOUT_DEPARTMENT = """
UNWIND $rows AS row
MATCH (r:EcommerceReview {review_id: row.review_id})
MATCH (d:EcommerceDepartment {department_id: row.department_id})
MERGE (r)-[:ABOUT_DEPARTMENT]->(d)
"""


UPSERT_REVIEW_IN_CLASS = """
UNWIND $rows AS row
MATCH (r:EcommerceReview {review_id: row.review_id})
MATCH (c:EcommerceClass {class_id: row.class_id})
MERGE (r)-[:IN_CLASS]->(c)
"""


UPSERT_REVIEW_IN_DIVISION = """
UNWIND $rows AS row
MATCH (r:EcommerceReview {review_id: row.review_id})
MATCH (d:EcommerceDivision {division_id: row.division_id})
MERGE (r)-[:IN_DIVISION]->(d)
"""


UPSERT_CLASS_BELONGS_TO_DEPARTMENT = """
UNWIND $rows AS row
MATCH (c:EcommerceClass {class_id: row.class_id})
MATCH (d:EcommerceDepartment {department_id: row.department_id})
MERGE (c)-[:BELONGS_TO_DEPARTMENT]->(d)
"""


def _clean_scalar(value):
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return bool(value)

    if hasattr(value, "item"):
        value = value.item()

    return value


def _iter_batches(
    path: Path,
    batch_size: int,
) -> Iterator[list[dict]]:
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


def _run_batched(
    session,
    query: str,
    path: Path,
) -> int:
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
        REVIEW_NODES,
        PRODUCT_NODES,
        DEPARTMENT_NODES,
        CLASS_NODES,
        DIVISION_NODES,
        REVIEW_REVIEWS_PRODUCT,
        REVIEW_ABOUT_DEPARTMENT,
        REVIEW_IN_CLASS,
        REVIEW_IN_DIVISION,
        CLASS_BELONGS_TO_DEPARTMENT,
    ]

    missing = [path for path in required if not path.exists()]

    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Thiếu E-commerce KG CSV. "
            "Hãy chạy prepare_ecommerce_kg.py trước:\n"
            + joined
        )

    driver = Neo4jClient.get_driver()

    try:
        with _open_session(driver) as session:
            if REPLACE_ECOMMERCE_KG:
                print("Deleting existing EcommerceKG subgraph...")
                session.run(
                    "MATCH (n:EcommerceKG) DETACH DELETE n"
                ).consume()

            print("Creating constraints...")
            for query in CONSTRAINTS:
                session.run(query).consume()

            print("Loading departments...")
            _run_batched(
                session,
                UPSERT_DEPARTMENTS,
                DEPARTMENT_NODES,
            )

            print("Loading classes...")
            _run_batched(
                session,
                UPSERT_CLASSES,
                CLASS_NODES,
            )

            print("Loading divisions...")
            _run_batched(
                session,
                UPSERT_DIVISIONS,
                DIVISION_NODES,
            )

            print("Loading products...")
            _run_batched(
                session,
                UPSERT_PRODUCTS,
                PRODUCT_NODES,
            )

            print("Loading reviews...")
            _run_batched(
                session,
                UPSERT_REVIEWS,
                REVIEW_NODES,
            )

            print("Loading Review-[:REVIEWS]->Product...")
            _run_batched(
                session,
                UPSERT_REVIEW_REVIEWS_PRODUCT,
                REVIEW_REVIEWS_PRODUCT,
            )

            print(
                "Loading "
                "Review-[:ABOUT_DEPARTMENT]->Department..."
            )
            _run_batched(
                session,
                UPSERT_REVIEW_ABOUT_DEPARTMENT,
                REVIEW_ABOUT_DEPARTMENT,
            )

            print("Loading Review-[:IN_CLASS]->Class...")
            _run_batched(
                session,
                UPSERT_REVIEW_IN_CLASS,
                REVIEW_IN_CLASS,
            )

            print("Loading Review-[:IN_DIVISION]->Division...")
            _run_batched(
                session,
                UPSERT_REVIEW_IN_DIVISION,
                REVIEW_IN_DIVISION,
            )

            print(
                "Loading "
                "Class-[:BELONGS_TO_DEPARTMENT]->Department..."
            )
            _run_batched(
                session,
                UPSERT_CLASS_BELONGS_TO_DEPARTMENT,
                CLASS_BELONGS_TO_DEPARTMENT,
            )

            print("\nVerification:")
            result = session.run(
                """
                MATCH (r:EcommerceReview)
                OPTIONAL MATCH (r)-[:REVIEWS]->(p:EcommerceProduct)
                OPTIONAL MATCH (
                    r
                )-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
                OPTIONAL MATCH (r)-[:IN_CLASS]->(c:EcommerceClass)
                OPTIONAL MATCH (r)-[:IN_DIVISION]->(v:EcommerceDivision)
                RETURN
                    count(DISTINCT r) AS reviews,
                    count(DISTINCT p) AS products,
                    count(DISTINCT d) AS departments,
                    count(DISTINCT c) AS classes,
                    count(DISTINCT v) AS divisions
                """
            ).single()

            print(dict(result) if result is not None else {})

        print("\nE-commerce KG load complete.")

    finally:
        Neo4jClient.close_driver()


if __name__ == "__main__":
    main()
