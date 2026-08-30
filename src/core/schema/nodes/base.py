from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseNode(BaseModel):
    """
    Thuộc tính chung cho mọi node trong Knowledge Graph.

    node_id:
        ID ổn định để dùng làm khóa trong graph.
        Nên sinh deterministic từ code thay vì UUID ngẫu nhiên khi seed nhiều lần.

    schema_version:
        Hỗ trợ nâng cấp schema sau này.

    source_name/source_url:
        Nguồn tri thức dùng để tạo node.
        Quan trọng với dữ liệu y tế để có thể truy vết.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    node_id: str = Field(min_length=1)
    schema_version: str = "1.0"

    source_name: str | None = None
    source_url: str | None = None

    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
