from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.prediction import service as prediction_service
from app.prediction.routes import router


class FakeClothingCategoryPipeline:
    def __init__(self) -> None:
        self.classes_ = ["Bottoms", "Dresses", "Intimate", "Jackets", "Tops", "Trend"]
        self.last_input = None

    def predict(self, input_data):
        self.last_input = input_data
        return ["Tops"]

    def predict_proba(self, input_data):
        self.last_input = input_data
        return [[0.012, 0.051, 0.008, 0.024, 0.8732, 0.0318]]


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _patch_clothing_category_model(monkeypatch) -> FakeClothingCategoryPipeline:
    fake_pipeline = FakeClothingCategoryPipeline()
    monkeypatch.setattr(
        prediction_service,
        "_load_clothing_category_pipeline",
        lambda: fake_pipeline,
    )
    monkeypatch.setattr(
        prediction_service,
        "_load_clothing_category_metadata",
        lambda: {"classes": fake_pipeline.classes_},
    )
    return fake_pipeline


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


def test_clothing_category_rejects_missing_body() -> None:
    response = _client().post("/customer-behavior/clothing-category/v1/predict")

    assert response.status_code == 400
    assert response.json() == {
        "error": "Thiếu thuộc tính bắt buộc",
        "details": [
            {
                "field": "text",
                "message": "text là bắt buộc và không được rỗng",
            }
        ],
        "missingFields": ["text"],
    }


def test_clothing_category_requires_text() -> None:
    response = _client().post(
        "/customer-behavior/clothing-category/v1/predict",
        json={"rating": 5},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Thiếu thuộc tính bắt buộc",
        "details": [
            {
                "field": "text",
                "message": "text là bắt buộc và không được rỗng",
            }
        ],
        "missingFields": ["text"],
    }


def test_clothing_category_rejects_blank_text() -> None:
    response = _client().post(
        "/customer-behavior/clothing-category/v1/predict",
        json={"text": "   "},
    )

    assert response.status_code == 400
    assert response.json()["details"] == [
        {
            "field": "text",
            "message": "text là bắt buộc và không được rỗng",
        }
    ]


def test_clothing_category_accepts_nullable_optional_fields(monkeypatch) -> None:
    fake_pipeline = _patch_clothing_category_model(monkeypatch)

    response = _client().post(
        "/customer-behavior/clothing-category/v1/predict",
        json={
            "text": "Love this soft casual blouse for everyday outfits.",
            "age": None,
            "rating": None,
            "positiveFeedbackCount": None,
            "recommendedInd": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["prediction"] == "Tops"
    assert response.json()["providedFields"] == ["text"]
    assert fake_pipeline.last_input.columns.tolist() == [
        "Age",
        "Rating",
        "Positive Feedback Count",
        "Recommended IND",
        "Combined Text",
    ]
    optional_columns = ["Age", "Rating", "Positive Feedback Count", "Recommended IND"]
    assert fake_pipeline.last_input[optional_columns].isna().all().all()


def test_clothing_category_rejects_invalid_optional_ranges() -> None:
    response = _client().post(
        "/customer-behavior/clothing-category/v1/predict",
        json={
            "text": "The jacket looks good but the sizing feels off.",
            "age": 150,
            "rating": 6,
            "positiveFeedbackCount": -1,
            "recommendedInd": 2,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Dữ liệu đầu vào không hợp lệ"
    assert {item["field"] for item in response.json()["details"]} == {
        "age",
        "rating",
        "positiveFeedbackCount",
        "recommendedInd",
    }


def test_clothing_category_prediction_success_contract(monkeypatch) -> None:
    _patch_clothing_category_model(monkeypatch)

    response = _client().post(
        "/customer-behavior/clothing-category/v1/predict",
        json={
            "text": "Beautiful top, light fabric, great with jeans.",
            "rating": 5,
            "recommendedInd": 1,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "prediction": "Tops",
        "confidence": 87.32,
        "probabilities": {
            "Bottoms": 1.2,
            "Dresses": 5.1,
            "Intimate": 0.8,
            "Jackets": 2.4,
            "Tops": 87.32,
            "Trend": 3.18,
        },
        "providedFields": ["text", "rating", "recommendedInd"],
        "providedFieldCount": 3,
    }


def test_clothing_category_openapi_exposes_request_and_response_schema() -> None:
    schema = _client().get("/openapi.json").json()
    operation = schema["paths"]["/customer-behavior/clothing-category/v1/predict"]["post"]

    request_ref = operation["requestBody"]["content"]["application/json"]["schema"]["anyOf"][0][
        "$ref"
    ]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    error_ref = operation["responses"]["400"]["content"]["application/json"]["schema"]["$ref"]

    assert request_ref.endswith("/ClothingCategoryPredictionRequest")
    assert response_ref.endswith("/ClothingCategoryPredictionResponse")
    assert error_ref.endswith("/PredictionErrorResponse")
    assert operation["summary"] == "Phân loại danh mục sản phẩm quần áo từ review khách hàng"

    request_schema = schema["components"]["schemas"]["ClothingCategoryPredictionRequest"]
    response_schema = schema["components"]["schemas"]["ClothingCategoryPredictionResponse"]

    assert request_schema["required"] == ["text"]
    assert set(request_schema["properties"]) == {
        "text",
        "age",
        "rating",
        "positiveFeedbackCount",
        "recommendedInd",
    }
    assert set(response_schema["properties"]) == {
        "prediction",
        "confidence",
        "probabilities",
        "providedFields",
        "providedFieldCount",
    }


def test_hi_is_plain_text() -> None:
    response = _client().get("/hi")

    assert response.status_code == 200
    assert response.text == "Hello World"
