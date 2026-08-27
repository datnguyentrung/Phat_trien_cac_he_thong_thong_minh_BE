from typing import Literal

from pydantic import Field

from .base import BaseEdge


class DiseaseHasConsultationNeedEdge(BaseEdge):
    """
    Edge:
        BỆNH --HAS_CONSULTATION_NEED--> NHU CẦU TƯ VẤN

    Ý nghĩa:
        Với bệnh này, chatbot hỗ trợ những loại nhu cầu tư vấn nào.

    Ví dụ:
        Đái tháo đường type 2
            --HAS_CONSULTATION_NEED-->
        Mua thiết bị theo dõi
    """

    relation: Literal["HAS_CONSULTATION_NEED"] = "HAS_CONSULTATION_NEED"

    priority: int = Field(
        default=100,
        ge=0,
        description="Độ ưu tiên khi chatbot sắp xếp các hướng tư vấn",
    )

    condition_note: str | None = Field(
        default=None,
        description=(
            "Ghi chú điều kiện áp dụng edge nếu có. "
            "Không dùng để chứa liều dùng hoặc kê đơn cá nhân hóa."
        ),
    )
