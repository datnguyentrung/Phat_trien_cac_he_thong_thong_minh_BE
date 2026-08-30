
from pydantic import Field

from .base import BaseNode


class DiseaseNode(BaseNode):
    """
    Node BỆNH.

    Mục đích:
    - Đại diện cho một bệnh/condition chuẩn trong Knowledge Graph.
    - Là node trung tâm để nối sang nhu cầu tư vấn và cảnh báo.

    Lưu ý:
    - Không nên tự suy ra mô tả bệnh chỉ từ kết quả search sản phẩm Long Châu.
    - description/standard_code nên đến từ nguồn y khoa đáng tin cậy
      hoặc dữ liệu được quản trị thủ công.
    """

    code: str = Field(
        min_length=1,
        description="Mã bệnh nội bộ ổn định, ví dụ DIABETES_TYPE_2",
    )
    name: str = Field(
        min_length=1,
        description="Tên chuẩn của bệnh",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Tên đồng nghĩa/tên thường gọi",
    )

    description: str | None = Field(
        default=None,
        description="Mô tả ngắn, dùng để chatbot hiểu ngữ cảnh bệnh",
    )

    disease_group: str | None = Field(
        default=None,
        description="Nhóm bệnh lớn, nếu hệ thống cần phân nhóm",
    )

    standard_code: str | None = Field(
        default=None,
        description="Mã chuẩn y khoa nếu có, ví dụ ICD-10",
    )
