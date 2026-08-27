from typing import Literal

from pydantic import Field

from .base import BaseEdge


class DiseaseHasWarningEdge(BaseEdge):
    """
    Edge:
        BỆNH --HAS_WARNING--> CẢNH BÁO

    Ý nghĩa:
        Khi chatbot đang tư vấn trong ngữ cảnh bệnh này,
        cảnh báo nào cần được xem xét/hiển thị.
    """

    relation: Literal["HAS_WARNING"] = "HAS_WARNING"

    priority: int = Field(
        default=100,
        ge=0,
        description="Độ ưu tiên hiển thị cảnh báo",
    )

    trigger_note: str | None = Field(
        default=None,
        description="Ghi chú về thời điểm/ngữ cảnh cảnh báo được áp dụng",
    )
