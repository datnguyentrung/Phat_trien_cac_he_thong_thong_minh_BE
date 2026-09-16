
from pydantic import BaseModel, ConfigDict, Field


class BaseEdge(BaseModel):
    """
    Thuộc tính chung cho mọi edge.

    rationale:
        Giải thích tại sao 2 node được nối với nhau.

    evidence:
        Bằng chứng ngắn hoặc ghi chú nguồn để audit quan hệ.

    confidence:
        Mức tin cậy của quan hệ nếu edge được sinh bán tự động.
        Với edge được curate thủ công có thể để 1.0.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    edge_id: str = Field(min_length=1)

    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)

    relation: str = Field(min_length=1)

    rationale: str | None = None
    evidence: str | None = None

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_active: bool = True
