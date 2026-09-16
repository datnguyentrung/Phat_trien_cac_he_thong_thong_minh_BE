from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClothingCategoryPredictionRequest(BaseModel):
    """Schema request cho FE gọi API phân loại danh mục quần áo.

    FE gửi `text` là review bắt buộc; các field còn lại có thể bỏ qua hoặc gửi
    `null`. Kiểu runtime để `Any` nhằm cho service tự chuẩn hóa và trả HTTP 400
    với thông báo tiếng Việt, thay vì để FastAPI trả 422 khó đồng bộ với các
    prediction API cũ.
    """

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "required": ["text"],
            "examples": [
                {
                    "text": "Beautiful soft blouse, fits perfectly and looks great with jeans.",
                    "age": None,
                    "rating": None,
                    "positiveFeedbackCount": None,
                    "recommendedInd": None,
                }
            ],
        },
    )

    text: Any = Field(
        default=None,
        description="Bắt buộc. Nội dung review của khách hàng, không được rỗng.",
        json_schema_extra={"type": "string", "minLength": 1},
    )
    age: Any = Field(
        default=None,
        description="Tuổi khách hàng. Có thể null; nếu có giá trị thì phải thỏa 0 < age <= 100.",
        json_schema_extra={"anyOf": [{"type": "number"}, {"type": "null"}]},
    )
    rating: Any = Field(
        default=None,
        description="Điểm đánh giá sản phẩm. Có thể null; nếu có giá trị thì nằm trong 1..5.",
        json_schema_extra={"anyOf": [{"type": "integer"}, {"type": "null"}]},
    )
    positiveFeedbackCount: Any = Field(
        default=None,
        description="Số lượt phản hồi tích cực. Có thể null; nếu có giá trị thì phải >= 0.",
        json_schema_extra={"anyOf": [{"type": "number"}, {"type": "null"}]},
    )
    recommendedInd: Any = Field(
        default=None,
        description="Cờ khách hàng có recommend sản phẩm hay không. Có thể null; nhận 0 hoặc 1.",
        json_schema_extra={"anyOf": [{"type": "integer"}, {"type": "null"}]},
    )


class ClothingCategoryPredictionResponse(BaseModel):
    """Schema response thành công để FE render kết quả dự đoán.

    `prediction` là danh mục có xác suất cao nhất, `confidence` và từng giá trị
    trong `probabilities` đều là phần trăm 0..100. `providedFields` giúp FE biết
    backend đã dùng những field nào do người dùng thật sự nhập.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prediction": "Tops",
                    "confidence": 90.42,
                    "probabilities": {
                        "Bottoms": 1.95,
                        "Dresses": 0.55,
                        "Intimate": 0.88,
                        "Jackets": 5.97,
                        "Tops": 90.42,
                        "Trend": 0.23,
                    },
                    "providedFields": ["text"],
                    "providedFieldCount": 1,
                }
            ]
        },
    )

    prediction: str = Field(description="Danh mục quần áo được model dự đoán.")
    confidence: float | None = Field(
        default=None,
        description="Độ tin cậy của nhãn dự đoán, tính theo phần trăm 0..100.",
    )
    probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Xác suất theo từng danh mục, mỗi giá trị là phần trăm 0..100.",
    )
    providedFields: list[str] = Field(
        default_factory=list,
        description="Danh sách field FE gửi lên và không null/rỗng.",
    )
    providedFieldCount: int = Field(
        description="Số lượng field hợp lệ backend nhận được từ request."
    )


class PredictionErrorDetail(BaseModel):
    """Một lỗi validation cụ thể theo field để FE highlight input tương ứng."""

    field: str = Field(description="Tên field trong request gây lỗi.")
    message: str = Field(description="Thông báo lỗi tiếng Việt có thể hiển thị cho người dùng.")


class PredictionErrorResponse(BaseModel):
    """Schema lỗi HTTP 400 chung cho endpoint clothing category."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "Dữ liệu đầu vào không hợp lệ",
                    "details": [
                        {
                            "field": "rating",
                            "message": "rating phải nằm trong 1..5",
                        }
                    ],
                }
            ]
        },
    )

    error: str = Field(description="Thông báo lỗi tổng quát.")
    details: list[PredictionErrorDetail] = Field(
        default_factory=list,
        description="Danh sách lỗi chi tiết theo field.",
    )
    missingFields: list[str] = Field(
        default_factory=list,
        description="Danh sách field bắt buộc còn thiếu, nếu có.",
    )
    message: str | None = Field(
        default=None,
        description="Chi tiết lỗi bổ sung cho các lỗi ép kiểu hoặc runtime validation.",
    )
