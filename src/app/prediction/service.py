import json
from functools import cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MODELS_DIR = _PROJECT_ROOT / "models"
_CUSTOMER_BEHAVIOR_ARTIFACT_DIR = _PROJECT_ROOT / "customer_behavior" / "artifacts"
_CLOTHING_CATEGORY_FIELDS = [
    "Age",
    "Rating",
    "Positive Feedback Count",
    "Recommended IND",
    "Combined Text",
]
_CLOTHING_OPTIONAL_FIELD_MAP = {
    "age": "Age",
    "rating": "Rating",
    "positiveFeedbackCount": "Positive Feedback Count",
    "recommendedInd": "Recommended IND",
}
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


@cache
def _load_clothing_category_pipeline():
    """Nạp pipeline phân loại danh mục quần áo một lần cho toàn tiến trình.

    Pipeline này được lưu từ notebook `customer_behavior/notebook/preprocessor.ipynb`
    và đã chứa đầy đủ bước tiền xử lý: impute dữ liệu thiếu, scale số liệu,
    TF-IDF cho review và model Logistic Regression. Controller/service chỉ
    cần truyền một `pandas.DataFrame` đúng schema, tuyệt đối không fit lại
    trên dữ liệu người dùng để tránh lệch preprocessing so với lúc train.
    """
    return joblib.load(
        _CUSTOMER_BEHAVIOR_ARTIFACT_DIR / "ecommerce_interest_pipeline.joblib"
    )


@cache
def _load_clothing_category_metadata() -> dict[str, Any]:
    """Đọc metadata đi kèm model để lấy danh sách class và thông tin schema.

    Metadata giúp service trả xác suất theo đúng tên danh mục (`Bottoms`,
    `Dresses`, `Intimate`, `Jackets`, `Tops`, `Trend`) ngay cả khi adapter model
    không expose đầy đủ thuộc tính `classes_`. Hàm được cache vì file JSON không
    thay đổi trong runtime bình thường.
    """
    with open(
        _CUSTOMER_BEHAVIOR_ARTIFACT_DIR / "ecommerce_interest_metadata.json",
        encoding="utf-8",
    ) as metadata_file:
        return json.load(metadata_file)


def _is_missing(value: Any) -> bool:
    """Kiểm tra giá trị request có nên xem là thiếu hay không.

    API cho phép các trường ngoài `text` nhận `null`; chuỗi rỗng cũng được xem
    như không cung cấp để tránh lỗi ép kiểu không cần thiết. Các giá trị
    thiếu sẽ được đưa vào dataframe dưới dạng `numpy.nan`, sau đó imputer đã
    train trong pipeline sẽ tự xử lý.
    """
    return value is None or value == ""


def _optional_float(features: dict[str, Any], public_key: str, model_key: str) -> float:
    """Chuẩn hóa một trường số nullable từ request sang cột model.

    `public_key` là tên field client gửi lên, còn `model_key` là tên cột đúng
    theo notebook. Nếu client không gửi hoặc gửi `null`, hàm trả `np.nan`; nếu
    có giá trị nhưng không ép được sang số, hàm báo `PredictionValidationError`
    để route trả HTTP 400 thống nhất với các endpoint dự đoán khác.
    """
    value = features.get(public_key)
    if _is_missing(value):
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PredictionValidationError(
            {
                "error": "Dữ liệu đầu vào không hợp lệ",
                "field": public_key,
                "message": f"{model_key} phải là số",
            }
        ) from exc


def _validate_clothing_optional_fields(features: dict[str, Any]) -> dict[str, float]:
    """Validate các trường phụ của API phân loại danh mục quần áo.

    Hàm trả về dictionary dùng trực tiếp để tạo dataframe input cho pipeline.
    Các trường phụ được phép thiếu/null để model dùng imputer, nhưng nếu
    người dùng có truyền giá trị thì phải nằm trong miền hợp lệ đã mô tả từ
    notebook: tuổi 1..100, rating 1..5, recommended 0/1 và positive feedback
    không âm.
    """
    normalized = {
        model_key: _optional_float(features, public_key, model_key)
        for public_key, model_key in _CLOTHING_OPTIONAL_FIELD_MAP.items()
    }

    validation_errors = []
    age = normalized["Age"]
    rating = normalized["Rating"]
    positive_feedback_count = normalized["Positive Feedback Count"]
    recommended_ind = normalized["Recommended IND"]

    if not np.isnan(age) and not 0 < age <= 100:
        validation_errors.append({"field": "age", "message": "age phải thỏa 0 < age <= 100"})
    if not np.isnan(rating) and rating not in {1, 2, 3, 4, 5}:
        validation_errors.append({"field": "rating", "message": "rating phải nằm trong 1..5"})
    if not np.isnan(recommended_ind) and recommended_ind not in {0, 1}:
        validation_errors.append(
            {"field": "recommendedInd", "message": "recommendedInd phải là 0 hoặc 1"}
        )
    if not np.isnan(positive_feedback_count) and positive_feedback_count < 0:
        validation_errors.append(
            {
                "field": "positiveFeedbackCount",
                "message": "positiveFeedbackCount phải >= 0",
            }
        )

    if validation_errors:
        raise PredictionValidationError(
            {
                "error": "Dữ liệu đầu vào không hợp lệ",
                "details": validation_errors,
            }
        )
    return normalized


def _clothing_probability_labels(model: Any, metadata: dict[str, Any]) -> list[str]:
    """Lấy danh sách nhãn tương ứng với thứ tự xác suất của model.

    Với sklearn pipeline, class thường nằm ở `pipeline.classes_`; một số phiên
    bản/adapter có thể chỉ expose ở step cuối `named_steps["model"].classes_`.
    Nếu cả hai không có, service dùng metadata đã export từ notebook để vẫn trả
    response dễ đọc cho client.
    """
    classes = getattr(model, "classes_", None)
    if classes is None and hasattr(model, "named_steps"):
        final_model = model.named_steps.get("model")
        classes = getattr(final_model, "classes_", None)
    if classes is None:
        classes = metadata.get("classes", [])
    return [str(item) for item in classes]


def predict_clothing_category(features: dict[str, Any]) -> dict[str, Any]:
    """Phân loại danh mục sản phẩm quần áo dựa trên review khách hàng.

    Cách dùng: route nhận JSON từ client rồi truyền nguyên `dict` vào hàm này.
    Trường bắt buộc là `text` và được map sang `Combined Text` đúng schema
    notebook; các trường `age`, `rating`, `positiveFeedbackCount`,
    `recommendedInd` là tùy chọn, có thể null, và sẽ được pipeline xử lý missing
    bằng imputer đã học khi train. Kết quả trả về gồm nhãn dự đoán, confidence,
    bảng xác suất theo từng danh mục và danh sách field client thật sự cung cấp.
    """
    text = features.get("text")
    if not isinstance(text, str) or not text.strip():
        raise PredictionValidationError(
            {
                "error": "Thiếu thuộc tính bắt buộc",
                "details": [
                    {
                        "field": "text",
                        "message": "text là bắt buộc và không được rỗng",
                    }
                ],
                "missingFields": ["text"],
            }
        )

    normalized_optional = _validate_clothing_optional_fields(features)
    input_data = pd.DataFrame(
        [
            {
                **normalized_optional,
                "Combined Text": text.strip(),
            }
        ],
        columns=_CLOTHING_CATEGORY_FIELDS,
    )

    pipeline = _load_clothing_category_pipeline()
    metadata = _load_clothing_category_metadata()
    prediction = str(pipeline.predict(input_data)[0])

    probabilities: dict[str, float] = {}
    confidence = None
    if hasattr(pipeline, "predict_proba"):
        probability_values = pipeline.predict_proba(input_data)[0]
        labels = _clothing_probability_labels(pipeline, metadata)
        probabilities = {
            label: round(float(probability) * 100, 2)
            for label, probability in zip(labels, probability_values, strict=False)
        }
        confidence = probabilities.get(prediction)
        if confidence is None and len(probability_values):
            confidence = round(float(np.max(probability_values)) * 100, 2)

    provided_fields = [
        field
        for field in ["text", *_CLOTHING_OPTIONAL_FIELD_MAP]
        if field in features and not _is_missing(features[field])
    ]
    return {
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": probabilities,
        "providedFields": provided_fields,
        "providedFieldCount": len(provided_fields),
    }


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
