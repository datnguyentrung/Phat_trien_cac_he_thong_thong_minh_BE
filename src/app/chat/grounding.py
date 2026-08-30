import re

_MEDICATION_TERMS = re.compile(
    r"\b(thuốc|bệnh|đau|triệu chứng|hoạt chất|liều|điều trị|dị ứng|"
    r"tương tác|chống chỉ định|mang thai|cho con bú|sản phẩm|thực phẩm bổ sung)\b",
    flags=re.IGNORECASE,
)

UNGROUNDED_MEDICATION_MESSAGE = """Mình chưa thể đưa ra thông tin thuốc hoặc sản phẩm cụ thể vì lượt trả lời này chưa đối chiếu được dữ liệu từ công cụ tư vấn.

Để bảo đảm an toàn, mình sẽ không suy diễn công dụng, liều dùng, chống chỉ định hay mức độ phù hợp từ kiến thức chung hoặc chỉ từ tên sản phẩm.

Bạn có thể nêu rõ tình trạng cần tư vấn và từ khóa sản phẩm. Tuổi, thai kỳ hoặc cho con bú, dị ứng, bệnh nền và các thuốc đang dùng cũng là những thông tin quan trọng nếu chúng có thể ảnh hưởng đến an toàn.

Vui lòng thử lại; khi Knowledge Graph và nguồn sản phẩm được đối chiếu thành công, mình sẽ trình bày cảnh báo, lựa chọn tham khảo và giới hạn dữ liệu theo cấu trúc đầy đủ."""


def requires_medication_grounding(message: str) -> bool:
    return _MEDICATION_TERMS.search(message) is not None
