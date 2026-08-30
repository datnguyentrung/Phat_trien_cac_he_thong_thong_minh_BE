"""
Ví dụ seed nhỏ để kiểm tra schema.
Đây chỉ là ví dụ cấu trúc, không phải nội dung kê đơn.
"""

from core.schema import (
    ConsultationNeedNode,
    ConsultationNeedType,
    DiseaseHasConsultationNeedEdge,
    DiseaseHasWarningEdge,
    DiseaseNode,
    WarningNode,
    WarningSeverity,
    WarningType,
)

disease = DiseaseNode(
    node_id="disease:diabetes-type-2",
    code="DIABETES_TYPE_2",
    name="Đái tháo đường típ 2",
    aliases=["Tiểu đường típ 2"],
    description="Node ví dụ cho ngữ cảnh chatbot.",
)

need = ConsultationNeedNode(
    node_id="need:monitoring-device",
    code=ConsultationNeedType.MONITORING_DEVICE,
    name="Mua thiết bị theo dõi",
    description="Tìm các thiết bị phục vụ việc theo dõi chỉ số liên quan.",
    long_chau_category_hints=[
        "Thiết bị y tế",
        "Dụng cụ theo dõi",
        "Máy, que thử đường huyết",
    ],
    long_chau_category_slugs=[
        "trang-thiet-bi-y-te",
        "trang-thiet-bi-y-te/dung-cu-theo-doi",
        "trang-thiet-bi-y-te/may-que-thu-duong-huyet",
    ],
)

warning = WarningNode(
    node_id="warning:medical-consultation",
    code="MEDICAL_CONSULTATION",
    title="Lưu ý khi tham khảo thuốc",
    message=(
        "Thông tin từ chatbot chỉ mang tính tham khảo và không thay thế "
        "đánh giá của bác sĩ hoặc dược sĩ."
    ),
    warning_type=WarningType.GENERAL,
    severity=WarningSeverity.IMPORTANT,
    action_text="Tham khảo bác sĩ hoặc dược sĩ trước khi sử dụng thuốc.",
)

edge_1 = DiseaseHasConsultationNeedEdge(
    edge_id="edge:diabetes-type-2:monitoring-device",
    source_node_id=disease.node_id,
    target_node_id=need.node_id,
    rationale="Bệnh được cấu hình hỗ trợ nhu cầu tìm thiết bị theo dõi.",
)

edge_2 = DiseaseHasWarningEdge(
    edge_id="edge:diabetes-type-2:medical-consultation",
    source_node_id=disease.node_id,
    target_node_id=warning.node_id,
    rationale="Áp dụng cảnh báo chung trong luồng tư vấn liên quan tới thuốc.",
)

print(disease.model_dump())
print(need.model_dump())
print(warning.model_dump())
print(edge_1.model_dump())
print(edge_2.model_dump())
