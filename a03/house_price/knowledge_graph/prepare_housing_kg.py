from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data" / "house_buying_dec29th_2025.csv"
NODES = ROOT / "data" / "nodes"
RELS = ROOT / "data" / "relationships"

HOUSE_NODES = NODES / "housing_houses.csv"
DISTRICT_NODES = NODES / "housing_districts.csv"
CITY_NODES = NODES / "housing_cities.csv"

HOUSE_LOCATED_IN = RELS / "housing_house_located_in_district.csv"
DISTRICT_BELONGS_TO = RELS / "housing_district_belongs_to_city.csv"

TARGET = "price_million_vnd"

DOMAIN_BOUNDS: dict[str, tuple[float, float]] = {
    "area_m2": (1, 1_000_000),
    "bedrooms": (0, 100),
    "bathrooms": (0, 100),
    "floors": (0, 100),
}


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "||".join(_normalize_text(part).casefold() for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _split_location(location: str) -> tuple[str, str]:
    """
    Dataset hiện tại có dạng:
        District/City-level area, Province/City
    Ví dụ:
        Long Biên, Hà Nội
        Gò Vấp, Hồ Chí Minh

    Không suy diễn Ward vì dataset không chứa ward.
    """
    parts = [_normalize_text(part) for part in str(location).split(",", 1)]

    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Unsupported location format: {location!r}")

    district, city = parts
    return district, city


def clean_for_kg(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Structural cleaning bám theo preprocessor của House Price:
    - remove exact duplicates
    - require positive target
    - normalize location
    - frontage -> nullable integer
    - invalid physical values -> NaN

    Khác với ML feature set:
    id/detail_url/title/timeline_hours vẫn được GIỮ làm metadata/provenance
    trên node House. Chúng chỉ bị loại khỏi ML input, không phải vô nghĩa
    đối với knowledge graph.
    """
    df = raw.copy()

    df = df.drop_duplicates().copy()

    df = df.loc[df[TARGET].notna()].copy()
    df = df.loc[df[TARGET] > 0].copy()

    df["location"] = (
        df["location"]
        .astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    location_parts = df["location"].str.split(",", n=1, expand=True)
    valid_location = (
        location_parts[0].fillna("").str.strip().ne("")
        & location_parts[1].fillna("").str.strip().ne("")
    )
    df = df.loc[valid_location].copy()

    df["frontage"] = df["frontage"].astype("Int64")

    for col, (low, high) in DOMAIN_BOUNDS.items():
        invalid = df[col].notna() & ~df[col].between(low, high, inclusive="both")
        df.loc[invalid, col] = np.nan

    return df


def build_graph_tables(df: pd.DataFrame) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    rows = []

    for record in df.to_dict(orient="records"):
        district_name, city_name = _split_location(record["location"])

        city_id = _stable_id("city", city_name)
        district_id = _stable_id("district", district_name, city_name)

        rows.append(
            {
                **record,
                "house_id": str(record["id"]),
                "district_id": district_id,
                "district_name": district_name,
                "city_id": city_id,
                "city_name": city_name,
            }
        )

    enriched = pd.DataFrame(rows)

    houses = enriched[
        [
            "house_id",
            "detail_url",
            "title",
            "location",
            "timeline_hours",
            "area_m2",
            "bedrooms",
            "bathrooms",
            "floors",
            "frontage",
            "price_million_vnd",
        ]
    ].rename(columns={"location": "location_raw"})

    districts = (
        enriched[
            [
                "district_id",
                "district_name",
                "city_id",
            ]
        ]
        .drop_duplicates(subset=["district_id"])
        .sort_values("district_name")
        .reset_index(drop=True)
    )

    cities = (
        enriched[
            [
                "city_id",
                "city_name",
            ]
        ]
        .drop_duplicates(subset=["city_id"])
        .sort_values("city_name")
        .reset_index(drop=True)
    )

    house_located_in = enriched[
        [
            "house_id",
            "district_id",
        ]
    ].drop_duplicates()

    district_belongs_to = enriched[
        [
            "district_id",
            "city_id",
        ]
    ].drop_duplicates()

    return (
        houses,
        districts,
        cities,
        house_located_in,
        district_belongs_to,
    )


def main() -> None:
    NODES.mkdir(parents=True, exist_ok=True)
    RELS.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(SOURCE)
    clean = clean_for_kg(raw)

    (
        houses,
        districts,
        cities,
        house_located_in,
        district_belongs_to,
    ) = build_graph_tables(clean)

    houses.to_csv(HOUSE_NODES, index=False)
    districts.to_csv(DISTRICT_NODES, index=False)
    cities.to_csv(CITY_NODES, index=False)
    house_located_in.to_csv(HOUSE_LOCATED_IN, index=False)
    district_belongs_to.to_csv(DISTRICT_BELONGS_TO, index=False)

    print("Housing KG tables created")
    print(f"- Raw rows:              {len(raw):,}")
    print(f"- Clean house rows:      {len(houses):,}")
    print(f"- District nodes:        {len(districts):,}")
    print(f"- City nodes:            {len(cities):,}")
    print(f"- LOCATED_IN rels:       {len(house_located_in):,}")
    print(f"- BELONGS_TO rels:       {len(district_belongs_to):,}")
    print()
    print("Output:")
    for path in [
        HOUSE_NODES,
        DISTRICT_NODES,
        CITY_NODES,
        HOUSE_LOCATED_IN,
        DISTRICT_BELONGS_TO,
    ]:
        print(" ", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
