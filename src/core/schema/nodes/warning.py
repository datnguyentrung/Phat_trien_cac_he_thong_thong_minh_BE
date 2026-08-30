
from pydantic import Field

from ..enums import WarningSeverity, WarningType
from .base import BaseNode


class WarningNode(BaseNode):
    """
    Node CẢNH BÁO.

    Mục đích:
    - Lưu các cảnh báo mà chatbot phải đưa ra khi tư vấn liên quan tới bệnh.
    - Tách cảnh báo thành node riêng để một cảnh báo có thể tái sử dụng
      cho nhiều bệnh nếu sau này mở rộng schema.

    Với nội dung y tế, nên luôn có nguồn để truy vết.
    """

    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)

    warning_type: WarningType = WarningType.GENERAL
    severity: WarningSeverity = WarningSeverity.CAUTION

    action_text: str | None = Field(
        default=None,
        description=(
            "Hành động khuyến nghị hiển thị cho người dùng, "
            "ví dụ tham khảo bác sĩ/dược sĩ trước khi dùng thuốc."
        ),
    )
