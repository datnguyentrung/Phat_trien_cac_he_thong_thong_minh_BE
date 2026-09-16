from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data" / "Womens Clothing E-Commerce Reviews.csv"
NODES = ROOT / "data" / "nodes"
RELS = ROOT / "data" / "relationships"

REVIEW_NODES = NODES / "ecommerce_reviews.csv"
PRODUCT_NODES = NODES / "ecommerce_products.csv"
DEPARTMENT_NODES = NODES / "ecommerce_departments.csv"
CLASS_NODES = NODES / "ecommerce_classes.csv"
DIVISION_NODES = NODES / "ecommerce_divisions.csv"

REVIEW_REVIEWS_PRODUCT = RELS / "ecommerce_review_reviews_product.csv"
REVIEW_ABOUT_DEPARTMENT = RELS / "ecommerce_review_about_department.csv"
REVIEW_IN_CLASS = RELS / "ecommerce_review_in_class.csv"
REVIEW_IN_DIVISION = RELS / "ecommerce_review_in_division.csv"
CLASS_BELONGS_TO_DEPARTMENT = RELS / "ecommerce_class_belongs_to_department.csv"

TARGET = "Department Name"


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "||".join(_normalize_text(part).casefold() for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def clean_for_kg(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Structural cleaning bám theo preprocessor E-commerce:

    - remove exact duplicates;
    - remove rows missing target Department Name;
    - normalize Division/Department/Class strings;
    - fill missing Title / Review Text with "";
    - normalize whitespace;
    - validate Age / Rating / Recommended IND / Positive Feedback Count;
    - invalid numerical values -> NaN;
    - create Combined Text.

    Lưu ý:
    - Clothing ID và Unnamed: 0 bị loại khỏi ML input, nhưng vẫn được giữ
      trong KG dưới vai trò định danh / provenance.
    - Division Name và Class Name bị loại khỏi ML input để tránh target
      leakage khi dự đoán Department Name, nhưng vẫn là tri thức hợp lệ
      trong KG và được lưu dưới dạng node/relationship.
    """
    df = raw.copy()

    # 1) Exact duplicates
    df = df.drop_duplicates().copy()

    # 2) Target phải tồn tại
    df = df.loc[df[TARGET].notna()].copy()

    # 3) Normalize categorical strings
    for col in ["Division Name", "Department Name", "Class Name"]:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

    # 4) Clean text
    for col in ["Title", "Review Text"]:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    # 5) Range validation
    df.loc[
        (df["Age"] <= 0) | (df["Age"] > 100),
        "Age",
    ] = np.nan

    df.loc[
        ~df["Rating"].isin([1, 2, 3, 4, 5]),
        "Rating",
    ] = np.nan

    df.loc[
        ~df["Recommended IND"].isin([0, 1]),
        "Recommended IND",
    ] = np.nan

    df.loc[
        df["Positive Feedback Count"] < 0,
        "Positive Feedback Count",
    ] = np.nan

    # 6) Derived text used by ML pipeline
    df["Combined Text"] = (
        df["Title"].fillna("").astype(str).str.strip()
        + " "
        + df["Review Text"].fillna("").astype(str).str.strip()
    ).str.strip()

    return df


def build_graph_tables(
    df: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    enriched_rows = []

    for record in df.to_dict(orient="records"):
        source_row_id = int(record["Unnamed: 0"])
        clothing_id = int(record["Clothing ID"])

        review_id = f"review_{source_row_id}"
        product_id = f"clothing_{clothing_id}"

        division_name = _normalize_text(record["Division Name"])
        department_name = _normalize_text(record["Department Name"])
        class_name = _normalize_text(record["Class Name"])

        division_id = _stable_id("division", division_name)
        department_id = _stable_id("department", department_name)
        class_id = _stable_id("class", class_name)

        enriched_rows.append(
            {
                **record,
                "source_row_id": source_row_id,
                "review_id": review_id,
                "product_id": product_id,
                "division_id": division_id,
                "division_name": division_name,
                "department_id": department_id,
                "department_name": department_name,
                "class_id": class_id,
                "class_name": class_name,
            }
        )

    enriched = pd.DataFrame(enriched_rows)

    reviews = enriched[
        [
            "review_id",
            "source_row_id",
            "Age",
            "Title",
            "Review Text",
            "Combined Text",
            "Rating",
            "Recommended IND",
            "Positive Feedback Count",
        ]
    ].rename(
        columns={
            "Age": "age",
            "Title": "title",
            "Review Text": "review_text",
            "Combined Text": "combined_text",
            "Rating": "rating",
            "Recommended IND": "recommended_ind",
            "Positive Feedback Count": "positive_feedback_count",
        }
    )

    products = (
        enriched[
            [
                "product_id",
                "Clothing ID",
            ]
        ]
        .drop_duplicates(subset=["product_id"])
        .rename(columns={"Clothing ID": "clothing_id"})
        .sort_values("clothing_id")
        .reset_index(drop=True)
    )

    departments = (
        enriched[
            [
                "department_id",
                "department_name",
            ]
        ]
        .drop_duplicates(subset=["department_id"])
        .sort_values("department_name")
        .reset_index(drop=True)
    )

    classes = (
        enriched[
            [
                "class_id",
                "class_name",
            ]
        ]
        .drop_duplicates(subset=["class_id"])
        .sort_values("class_name")
        .reset_index(drop=True)
    )

    divisions = (
        enriched[
            [
                "division_id",
                "division_name",
            ]
        ]
        .drop_duplicates(subset=["division_id"])
        .sort_values("division_name")
        .reset_index(drop=True)
    )

    review_reviews_product = enriched[
        [
            "review_id",
            "product_id",
        ]
    ].drop_duplicates()

    review_about_department = enriched[
        [
            "review_id",
            "department_id",
        ]
    ].drop_duplicates()

    review_in_class = enriched[
        [
            "review_id",
            "class_id",
        ]
    ].drop_duplicates()

    review_in_division = enriched[
        [
            "review_id",
            "division_id",
        ]
    ].drop_duplicates()

    # Source data hiện cho thấy mỗi Class Name thuộc đúng 1 Department Name.
    class_department_pairs = enriched[
        [
            "class_id",
            "department_id",
        ]
    ].drop_duplicates()

    ambiguous_classes = (
        class_department_pairs.groupby("class_id")["department_id"]
        .nunique()
    )

    if (ambiguous_classes > 1).any():
        bad = ambiguous_classes[ambiguous_classes > 1]
        raise ValueError(
            "Phát hiện Class Name thuộc nhiều Department Name; "
            "không thể tạo quan hệ hierarchy duy nhất:\n"
            + bad.to_string()
        )

    class_belongs_to_department = class_department_pairs

    return (
        reviews,
        products,
        departments,
        classes,
        divisions,
        review_reviews_product,
        review_about_department,
        review_in_class,
        review_in_division,
        class_belongs_to_department,
    )


def main() -> None:
    NODES.mkdir(parents=True, exist_ok=True)
    RELS.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(SOURCE)
    clean = clean_for_kg(raw)

    (
        reviews,
        products,
        departments,
        classes,
        divisions,
        review_reviews_product,
        review_about_department,
        review_in_class,
        review_in_division,
        class_belongs_to_department,
    ) = build_graph_tables(clean)

    reviews.to_csv(REVIEW_NODES, index=False)
    products.to_csv(PRODUCT_NODES, index=False)
    departments.to_csv(DEPARTMENT_NODES, index=False)
    classes.to_csv(CLASS_NODES, index=False)
    divisions.to_csv(DIVISION_NODES, index=False)

    review_reviews_product.to_csv(REVIEW_REVIEWS_PRODUCT, index=False)
    review_about_department.to_csv(REVIEW_ABOUT_DEPARTMENT, index=False)
    review_in_class.to_csv(REVIEW_IN_CLASS, index=False)
    review_in_division.to_csv(REVIEW_IN_DIVISION, index=False)
    class_belongs_to_department.to_csv(
        CLASS_BELONGS_TO_DEPARTMENT,
        index=False,
    )

    print("E-commerce KG tables created")
    print(f"- Raw rows:                 {len(raw):,}")
    print(f"- Clean review rows:        {len(reviews):,}")
    print(f"- Product nodes:            {len(products):,}")
    print(f"- Department nodes:         {len(departments):,}")
    print(f"- Class nodes:              {len(classes):,}")
    print(f"- Division nodes:           {len(divisions):,}")
    print(f"- REVIEWS rels:             {len(review_reviews_product):,}")
    print(f"- ABOUT_DEPARTMENT rels:    {len(review_about_department):,}")
    print(f"- IN_CLASS rels:            {len(review_in_class):,}")
    print(f"- IN_DIVISION rels:         {len(review_in_division):,}")
    print(
        f"- CLASS->DEPARTMENT rels:   "
        f"{len(class_belongs_to_department):,}"
    )

    print("\nOutput:")
    for path in [
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
    ]:
        print(" ", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
