from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
RAW = (
    PROJECT_ROOT / "diabetes" / "data" / "diabetes_binary_5050split_health_indicators_BRFSS2023.csv"
)
NODES = ROOT / "data" / "nodes"
RELS = ROOT / "data" / "relationships"

TARGET = "Diabetes_binary"
YES_NO_12_COLUMNS = ["KidneyDisease", "Asthma", "COPD"]
BINARY_01_COLUMNS = [
    "HighBP",
    "HighChol",
    "CholCheck",
    "Smoker",
    "Stroke",
    "HeartDiseaseorAttack",
    "PhysActivity",
    "HvyAlcoholConsump",
    "AnyHealthcare",
    "NoDocbcCost",
    "DiffWalk",
    "Sex",
]
ORDINAL_RANGES = {
    "GenHlth": (1, 5),
    "AgeGroup": (1, 13),
    "Education": (1, 6),
    "Income": (1, 11),
}
CONTINUOUS_RANGES = {
    "BMI": (10, 100),
    "MentHlth": (0, 30),
    "PhysHlth": (0, 30),
}

BINARY_FEATURE_META = [
    ("KidneyDisease", "condition", "Kidney disease"),
    ("HighBP", "condition", "High blood pressure"),
    ("HighChol", "condition", "High cholesterol"),
    ("Asthma", "condition", "Asthma"),
    ("COPD", "condition", "COPD"),
    ("Stroke", "condition", "Stroke"),
    ("HeartDiseaseorAttack", "condition", "Heart disease or heart attack"),
    ("DiffWalk", "condition", "Difficulty walking"),
    ("Diabetes_binary", "condition", "Diabetes"),
    ("CholCheck", "health_action", "Cholesterol check"),
    ("Smoker", "behavior", "Smoking"),
    ("PhysActivity", "behavior", "Physical activity"),
    ("HvyAlcoholConsump", "behavior", "Heavy alcohol consumption"),
    ("AnyHealthcare", "healthcare_access", "Has healthcare coverage/access"),
    ("NoDocbcCost", "healthcare_access", "Could not see doctor because of cost"),
    ("Sex", "demographic", "Sex code"),
]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().copy()
    df = df.loc[df[TARGET].isin([0.0, 1.0])].copy()

    for col in YES_NO_12_COLUMNS:
        df[col] = df[col].map({1.0: 1.0, 2.0: 0.0})

    for col in BINARY_01_COLUMNS:
        invalid = df[col].notna() & ~df[col].isin([0.0, 1.0])
        df.loc[invalid, col] = np.nan

    for col, (lo, hi) in ORDINAL_RANGES.items():
        invalid = df[col].notna() & ~df[col].between(lo, hi, inclusive="both")
        df.loc[invalid, col] = np.nan

    for col, (lo, hi) in CONTINUOUS_RANGES.items():
        invalid = df[col].notna() & ~df[col].between(lo, hi, inclusive="both")
        df.loc[invalid, col] = np.nan

    df[TARGET] = df[TARGET].astype(int)
    df = df.reset_index(drop=True)
    df.insert(0, "respondent_id", [f"R{i + 1:06d}" for i in range(len(df))])
    return df


def main():
    NODES.mkdir(parents=True, exist_ok=True)
    RELS.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW)
    clean = clean_data(raw)

    clean.to_csv(ROOT / "data" / "diabetes_clean_for_kg.csv", index=False)

    clean[
        [
            "respondent_id",
            "BMI",
            "MentHlth",
            "PhysHlth",
            "GenHlth",
            "AgeGroup",
            "Education",
            "Income",
        ]
    ].to_csv(NODES / "respondents.csv", index=False)

    concepts = pd.DataFrame(
        [
            {
                "concept_id": f"C_{feature.upper()}",
                "feature": feature,
                "category": category,
                "name": name,
            }
            for feature, category, name in BINARY_FEATURE_META
        ]
    )
    concepts.to_csv(NODES / "concepts.csv", index=False)

    edge_parts = []
    for feature, category, _ in BINARY_FEATURE_META:
        tmp = clean[["respondent_id", feature]].dropna().copy()
        tmp["concept_id"] = f"C_{feature.upper()}"
        tmp["value"] = tmp[feature].astype(int)
        tmp["source_feature"] = feature
        tmp["relation"] = (
            "HAS_DIABETES_STATUS"
            if feature == TARGET
            else "HAS_DEMOGRAPHIC_VALUE"
            if category == "demographic"
            else "HAS_HEALTH_INDICATOR"
        )
        edge_parts.append(
            tmp[["respondent_id", "concept_id", "relation", "value", "source_feature"]]
        )

    pd.concat(edge_parts, ignore_index=True).to_csv(RELS / "respondent_concepts.csv", index=False)

    print(f"Clean respondents: {len(clean):,}")
    print("Generated KG CSV files successfully.")


if __name__ == "__main__":
    main()
