from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.prediction.routes import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_diabetes_prediction_preserves_legacy_contract() -> None:
    response = _client().post(
        "/diabetes/v1/predict",
        json={"Glucose": 140, "BMI": 28.5},
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "prediction",
        "confidence",
        "providedFields",
        "providedFieldCount",
    }
    assert response.json()["providedFields"] == ["Glucose", "BMI"]


def test_diabetes_requires_at_least_two_fields() -> None:
    response = _client().post(
        "/diabetes/v1/predict",
        json={"Glucose": 140},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Cần nhập ít nhất 2 thuộc tính",
        "providedFields": ["Glucose"],
    }


def test_housing_missing_fields_preserves_legacy_error() -> None:
    response = _client().post(
        "/housing/v1/predict",
        json={"Area": 60},
    )

    assert response.status_code == 400
    assert response.json()["missingFields"] == ["City", "District"]


def test_housing_prediction_preserves_success_contract() -> None:
    response = _client().post(
        "/housing/v1/predict",
        json={"Area": 60, "City": "Hà Nội", "District": "Cầu Giấy"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"prediction"}
    assert isinstance(response.json()["prediction"], float)


def test_hi_is_plain_text() -> None:
    response = _client().get("/hi")

    assert response.status_code == 200
    assert response.text == "Hello World"
