from typing import Annotated, Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, PlainTextResponse

from app.prediction.service import (
    PredictionValidationError,
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


@router.get("/hi", response_class=PlainTextResponse)
async def hi() -> str:
    return "Hello World"
