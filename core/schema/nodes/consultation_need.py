
from pydantic import Field

from ..enums import ConsultationNeedType
from .base import BaseNode


class ConsultationNeedNode(BaseNode):
    """
    Node NHU CẦU TƯ VẤN.

    Đây không phải sản phẩm cụ thể.
    Nó mô tả người dùng đang muốn chatbot hỗ trợ theo hướng nào.

    4 loại đã chốt:
    - mua thuốc
    - mua thiết bị theo dõi
    - mua dụng cụ tiêm
    - mua sản phẩm hỗ trợ

    long_chau_category_hints:
        Chỉ là metadata kỹ thuật để tầng gọi API có thể ưu tiên/filter
        category của Long Châu. Không phải node Product/Category trong KG.
    """

    code: ConsultationNeedType
    name: str = Field(min_length=1)
    description: str | None = None

    long_chau_category_hints: list[str] = Field(
        default_factory=list,
        description=(
            "Gợi ý category/sub-category lấy từ dữ liệu Long Châu, "
            "ví dụ Thuốc, Thiết bị y tế, Dụng cụ theo dõi..."
        ),
    )

    long_chau_category_slugs: list[str] = Field(
        default_factory=list,
        description="Slug category tương ứng nếu API search hỗ trợ filter",
    )
