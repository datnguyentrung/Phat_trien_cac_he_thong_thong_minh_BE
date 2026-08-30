from functools import cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MODELS_DIR = _PROJECT_ROOT / "models"
_DIABETES_FIELDS = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]
_ZERO_AS_MISSING = [
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
]


@cache
def _load_diabetes_model():
    return joblib.load(_MODELS_DIR / "diabetes.sav")


@cache
def _load_housing_model():
    return joblib.load(_MODELS_DIR / "housing_price.sav")


def predict_diabetes(features: dict[str, Any]) -> dict[str, Any]:
    provided_fields = [
        field
        for field in _DIABETES_FIELDS
        if field in features and features[field] is not None and features[field] != ""
    ]
    if len(provided_fields) < 2:
        raise PredictionValidationError(
            {
                "error": "Cần nhập ít nhất 2 thuộc tính",
                "providedFields": provided_fields,
            }
        )

    row = {
        field: np.nan
        if features.get(field) is None or features.get(field) == ""
        else float(features[field])
        for field in _DIABETES_FIELDS
    }
    input_data = pd.DataFrame([row], columns=_DIABETES_FIELDS)
    for column in _ZERO_AS_MISSING:
        input_data[column] = input_data[column].replace(0, np.nan)

    model = _load_diabetes_model()
    prediction = model.predict(input_data)
    probabilities = model.predict_proba(input_data)
    predicted_class = int(prediction[0])
    confidence = float(probabilities[0][predicted_class] * 100)
    return {
        "prediction": predicted_class,
        "confidence": round(confidence, 2),
        "providedFields": provided_fields,
        "providedFieldCount": len(provided_fields),
    }


def _optional_number(features: dict[str, Any], key: str) -> float:
    value = features.get(key)
    return float(value) if value is not None else np.nan


def predict_housing(features: dict[str, Any]) -> dict[str, float]:
    required_fields = ["Area", "City", "District"]
    missing_fields = [
        field
        for field in required_fields
        if field not in features or features[field] is None or features[field] == ""
    ]
    if missing_fields:
        raise PredictionValidationError(
            {
                "error": "Thiếu thuộc tính bắt buộc",
                "missingFields": missing_fields,
            }
        )

    input_data = pd.DataFrame(
        [
            {
                "Area": float(features["Area"]),
                "Frontage": _optional_number(features, "Frontage"),
                "Access Road": _optional_number(features, "AccessRoad"),
                "Floors": _optional_number(features, "Floors"),
                "Bedrooms": _optional_number(features, "Bedrooms"),
                "Bathrooms": _optional_number(features, "Bathrooms"),
                "House direction": features.get("HouseDirection") or np.nan,
                "Balcony direction": features.get("BalconyDirection") or np.nan,
                "Legal status": features.get("LegalStatus") or np.nan,
                "Furniture state": features.get("FurnitureState") or np.nan,
                "City": features["City"],
                "District": features["District"],
            }
        ]
    )
    predicted_price = float(_load_housing_model().predict(input_data)[0])
    return {"prediction": round(predicted_price, 2)}


class PredictionValidationError(ValueError):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get("error", "Dữ liệu đầu vào không hợp lệ"))
        self.payload = payload
