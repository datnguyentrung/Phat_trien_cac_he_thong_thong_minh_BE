from typing import Annotated, Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, PlainTextResponse

from app.prediction.schemas import (
    ClothingCategoryPredictionRequest,
    ClothingCategoryPredictionResponse,
    PredictionErrorResponse,
)
from app.prediction.service import (
    PredictionValidationError,
    predict_clothing_category,
    predict_diabetes,
    predict_housing,
)

router = APIRouter()


def _invalid_body() -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "Request body phải là JSON"},
    )


@router.post("/diabetes/v1/predict")
async def diabetes_prediction(payload: Annotated[Any, Body()] = None):
    if not isinstance(payload, dict):
        return _invalid_body()
    try:
        return predict_diabetes(payload)
    except PredictionValidationError as exc:
        return JSONResponse(status_code=400, content=exc.payload)
    except (TypeError, ValueError) as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Dữ liệu đầu vào không hợp lệ",
                "message": str(exc),
            },
        )


@router.post("/housing/v1/predict")
async def housing_prediction(payload: Annotated[Any, Body()] = None):
    if not isinstance(payload, dict):
        return _invalid_body()
    try:
        return predict_housing(payload)
    except PredictionValidationError as exc:
        return JSONResponse(status_code=400, content=exc.payload)
    except (TypeError, ValueError) as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Dữ liệu đầu vào không hợp lệ",
                "message": str(exc),
            },
        )


# API cho FE:
# - Method/path: POST /customer-behavior/clothing-category/v1/predict
# - Request JSON: text bắt buộc; age, rating, positiveFeedbackCount,
#   recommendedInd có thể null hoặc bỏ qua.
# - Response 200: prediction, confidence, probabilities, providedFields,
#   providedFieldCount; các xác suất đều là phần trăm 0..100.
# - Response 400: error + details/missingFields để FE hiển thị lỗi theo field.
@router.post(
    "/customer-behavior/clothing-category/v1/predict",
    response_model=ClothingCategoryPredictionResponse,
    responses={
        400: {
            "model": PredictionErrorResponse,
            "description": "Request không hợp lệ hoặc thiếu field bắt buộc.",
        }
    },
    summary="Phân loại danh mục sản phẩm quần áo từ review khách hàng",
)
async def clothing_category_prediction(
    payload: Annotated[ClothingCategoryPredictionRequest | None, Body()] = None,
):
    """Nhận request từ FE và gọi model phân loại danh mục quần áo.

    Ví dụ FE gửi:
    `{"text": "Beautiful soft blouse", "rating": 5, "recommendedInd": 1}`.
    Route chuyển payload sang dict camelCase rồi gọi service. Service sẽ tạo
    dataframe đúng schema notebook và trả về danh mục dự đoán kèm xác suất.
    """
    if payload is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Thiếu thuộc tính bắt buộc",
                "details": [
                    {
                        "field": "text",
                        "message": "text là bắt buộc và không được rỗng",
                    }
                ],
                "missingFields": ["text"],
            },
        )
    try:
        return predict_clothing_category(payload.model_dump())
    except PredictionValidationError as exc:
        return JSONResponse(status_code=400, content=exc.payload)
    except (TypeError, ValueError) as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Dữ liệu đầu vào không hợp lệ",
                "message": str(exc),
            },
        )


@router.get("/hi", response_class=PlainTextResponse)
async def hi() -> str:
    return "Hello World"
