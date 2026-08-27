import re

from app.chat.markdown import FinalSummaryMarkdownStream

PRODUCTS = [
    {
        "sku": "P001",
        "name": "Paracetamol Stada 500mg",
        "webName": "Paracetamol Stada 500mg Hộp 20 viên",
        "imageUrl": (
            "https://cdn.nhathuoclongchau.com.vn/images/"
            "paracetamol-stada-500mg.jpg"
        ),
        "productUrl": (
            "https://nhathuoclongchau.com.vn/paracetamol-stada-500mg"
        ),
        "price": "55.000đ",
        "ingredients": "Paracetamol 500mg",
        "dosageForm": "Viên nén",
        "specification": "Hộp 20 viên",
        "brand": "Stada",
        "category": "Thuốc giảm đau",
    },
    {
        "sku": "P002",
        "name": "Panadol Extra 500mg",
        "webName": "Panadol Extra 500mg Hộp 20 viên",
        "imageUrl": (
            "https://cdn.nhathuoclongchau.com.vn/images/"
            "panadol-extra-500mg.jpg"
        ),
        "productUrl": "https://nhathuoclongchau.com.vn/panadol-extra-500mg",
        "price": "78.000đ",
        "ingredients": "Paracetamol 500mg, cafein 65mg",
        "dosageForm": "Viên nén",
        "specification": "Hộp 20 viên",
        "brand": "GSK",
        "category": "Thuốc giảm đau",
    },
    {
        "sku": "P003",
        "name": "Efferalgan 500mg",
        "webName": "Efferalgan 500mg Hộp 16 viên sủi",
        "imageUrl": (
            "https://cdn.nhathuoclongchau.com.vn/images/"
            "efferalgan-500mg.jpg"
        ),
        "productUrl": "https://nhathuoclongchau.com.vn/efferalgan-500mg",
        "price": "92.000đ",
        "ingredients": "Paracetamol 500mg",
        "dosageForm": "Viên sủi",
        "specification": "Hộp 16 viên",
        "brand": "UPSA",
        "category": "Thuốc giảm đau",
    },
    {
        "sku": "P004",
        "name": "Hapacol 650mg",
        "webName": "Hapacol 650mg Hộp 12 viên sủi",
        "imageUrl": (
            "https://cdn.nhathuoclongchau.com.vn/images/"
            "hapacol-650mg.jpg"
        ),
        "productUrl": "https://nhathuoclongchau.com.vn/hapacol-650mg",
        "price": "61.000đ",
        "ingredients": "Paracetamol 650mg",
        "dosageForm": "Viên sủi",
        "specification": "Hộp 12 viên",
        "brand": "DHG Pharma",
        "category": "Thuốc giảm đau",
    },
]

KG_SOURCE_URL = "https://www.who.int/initiatives/medication-without-harm"

EXPECTED_URLS = {
    product["productUrl"] for product in PRODUCTS
} | {product["imageUrl"] for product in PRODUCTS} | {KG_SOURCE_URL}

EXPECTED_HEADINGS = [
    "### Tóm tắt nhu cầu của bạn",
    "### Cảnh báo cần ưu tiên",
    "### Các sản phẩm được tìm thấy để tham khảo",
    "### Bảng đối chiếu nhanh",
    "### Kết luận an toàn",
    "### Nguồn và giới hạn dữ liệu",
]

# Ngôn ngữ chốt sale và claim y tế không được phép xuất hiện trong summary.
BANNED_PHRASES = [
    "PAS",
    "FOMO",
    "mua ngay",
    "chốt đơn",
    "giảm giá",
    "khuyến mãi",
    "ưu đãi",
    "nhanh tay",
    "số lượng có hạn",
    "bán chạy nhất",
    "tốt nhất",
    "số 1",
    "an toàn tuyệt đối",
    "khuyên dùng tuyệt đối",
    "chữa khỏi",
    "khỏi bệnh",
    "uống 1 viên",
    "mỗi ngày 2 lần",
    "hết đau sau",
    "phù hợp với mọi lứa tuổi",
    "an toàn cho phụ nữ mang thai",
    "chống chỉ định với",
    "tương tác với",
]


def _plain_words(markdown: str) -> int:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", markdown)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#|>*`_-]", " ", text)
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _markdown_urls(markdown: str) -> set[str]:
    return set(re.findall(r"\]\(([^)]+)\)", markdown))


def _assert_summary_contract(summary: str) -> None:
    lines = summary.splitlines()
    headings = [line for line in lines if line.startswith("### ")]

    assert headings == EXPECTED_HEADINGS
    assert not any(line.startswith(("# ", "## ")) for line in lines)

    lowered = summary.casefold()
    for phrase in BANNED_PHRASES:
        assert phrase.casefold() not in lowered

    assert 500 <= _plain_words(summary) <= 1600
    assert _markdown_urls(summary) == EXPECTED_URLS

    # Mọi ảnh trong summary phải lấy nguyên văn từ normalized data.
    image_destinations = set(re.findall(r"\]\(([^)]+\.(?:jpg|png|webp))\)", summary))
    assert image_destinations == {product["imageUrl"] for product in PRODUCTS}


CANONICAL_SUMMARY = """### Tóm tắt nhu cầu của bạn

> **Góc nhìn tư vấn:** Bạn đang tìm thông tin tham khảo cho tình trạng đau đầu và muốn xem các sản phẩm có thể đem ra trao đổi thêm với dược sĩ. Từ câu hỏi, mình ghi nhận nhu cầu chính là tìm sản phẩm giảm triệu chứng đau đầu cấp tính; chưa rõ thời gian kéo dài, tần suất, mức độ ảnh hưởng đến sinh hoạt, tiền sử bệnh nền, dị ứng thuốc, thai kỳ hoặc cho con bú, và danh sách thuốc đang dùng. Đây là những thông tin quan trọng vì chúng có thể thay đổi mức độ an toàn khi lựa chọn sản phẩm. Tư vấn trực tuyến chỉ giúp bạn hiểu dữ liệu sản phẩm và cảnh báo an toàn, không thay thế việc khám, chẩn đoán hoặc kê đơn của bác sĩ. Nếu cơn đau đầu xuất hiện đột ngột, dữ dội, kèm sốt cao, cứng cổ, rối loạn thị giác, yếu tay chân hoặc nói khó, bạn cần đến cơ sở y tế ngay thay vì tiếp tục tìm sản phẩm.

### Cảnh báo cần ưu tiên

- Từ knowledge graph, mục "đau đầu" có cảnh báo mức ưu tiên cao: đau đầu dữ dội xuất hiện đột ngột cần được đánh giá y tế khẩn cấp; không nên tự dùng sản phẩm giảm đau để che dấu triệu chứng.
- Cảnh báo thứ hai nhắc rằng người có tiền sử loét dạ dày, bệnh gan, bệnh thận, hen hoặc dị ứng với nhóm sản phẩm giảm đau cần hỏi dược sĩ trước khi dùng bất kỳ sản phẩm nào trong danh sách.
- Nếu bạn đang mang thai, cho con bú, hoặc đang dùng thuốc chống đông, thuốc điều trị tăng huyết áp, cần cung cấp thêm thông tin để đánh giá an toàn.
- Các cảnh báo trên được lấy từ dữ liệu knowledge graph và được tách riêng với lưu ý an toàn chung: không tự ý dùng kéo dài, không dùng nhiều sản phẩm cùng lúc nếu chưa rõ thành phần.
- Trường hợp xuất hiện dấu hiệu nguy hiểm hoặc bạn thuộc nhóm đối tượng đặc biệt, hãy gặp bác sĩ hoặc dược sĩ để được tư vấn trực tiếp thay vì tiếp tục chọn sản phẩm.

### Các sản phẩm được tìm thấy để tham khảo

#### 1) Paracetamol Stada 500mg

![Paracetamol Stada 500mg | https://nhathuoclongchau.com.vn/paracetamol-stada-500mg | 55.000đ](https://cdn.nhathuoclongchau.com.vn/images/paracetamol-stada-500mg.jpg)

**Giá tham khảo:** 55.000đ / Hộp

**Thành phần công bố:** Paracetamol 500mg

**Dạng bào chế và quy cách:** Viên nén; hộp 20 viên

**Vì sao sản phẩm xuất hiện:** Sản phẩm xuất hiện khi tìm kiếm từ khóa "thuốc đau đầu" trên Long Châu; kết quả nằm trong nhóm thuốc giảm đau, hạ sốt. Mình không khẳng định sản phẩm phù hợp với tình trạng của bạn.

**Điều cần kiểm tra trước khi dùng:** Cần xác nhận tiền sử dị ứng, bệnh gan, bệnh thận và các thuốc đang dùng với dược sĩ; dữ liệu hiện chưa xác minh mức độ an toàn cho từng đối tượng cụ thể.

**Nguồn sản phẩm:** [Xem tại Long Châu](https://nhathuoclongchau.com.vn/paracetamol-stada-500mg)

---

#### 2) Panadol Extra 500mg

![Panadol Extra 500mg | https://nhathuoclongchau.com.vn/panadol-extra-500mg | 78.000đ](https://cdn.nhathuoclongchau.com.vn/images/panadol-extra-500mg.jpg)

**Giá tham khảo:** 78.000đ / Hộp

**Thành phần công bố:** Paracetamol 500mg, cafein 65mg

**Dạng bào chế và quy cách:** Viên nén; hộp 20 viên

**Vì sao sản phẩm xuất hiện:** Sản phẩm xuất hiện khi tìm kiếm từ khóa "thuốc đau đầu" trên Long Châu và thuộc nhóm thuốc giảm đau, hạ sốt. Thành phần cafein được ghi nhận theo dữ liệu công bố; mình không suy diễn tác dụng của cafein cho tình trạng của bạn.

**Điều cần kiểm tra trước khi dùng:** Nếu bạn có bệnh tim, rối loạn giấc ngủ hoặc nhạy cảm với cafein, cần hỏi dược sĩ trước khi xem xét sản phẩm này.

**Nguồn sản phẩm:** [Xem tại Long Châu](https://nhathuoclongchau.com.vn/panadol-extra-500mg)

---

#### 3) Efferalgan 500mg

![Efferalgan 500mg | https://nhathuoclongchau.com.vn/efferalgan-500mg | 92.000đ](https://cdn.nhathuoclongchau.com.vn/images/efferalgan-500mg.jpg)

**Giá tham khảo:** 92.000đ / Hộp

**Thành phần công bố:** Paracetamol 500mg

**Dạng bào chế và quy cách:** Viên sủi; hộp 16 viên

**Vì sao sản phẩm xuất hiện:** Sản phẩm xuất hiện khi tìm kiếm từ khóa "thuốc đau đầu" trên Long Châu; dạng viên sủi được ghi nhận theo dữ liệu sản phẩm. Mình không so sánh hiệu quả giữa dạng viên nén và viên sủi vì dữ liệu hiện có không hỗ trợ điều đó.

**Điều cần kiểm tra trước khi dùng:** Người có bệnh thận hoặc đang theo chế độ ăn hạn chế natri cần hỏi dược sĩ trước khi xem xét dạng viên sủi.

**Nguồn sản phẩm:** [Xem tại Long Châu](https://nhathuoclongchau.com.vn/efferalgan-500mg)

---

#### 4) Hapacol 650mg

![Hapacol 650mg | https://nhathuoclongchau.com.vn/hapacol-650mg | 61.000đ](https://cdn.nhathuoclongchau.com.vn/images/hapacol-650mg.jpg)

**Giá tham khảo:** 61.000đ / Hộp

**Thành phần công bố:** Paracetamol 650mg

**Dạng bào chế và quy cách:** Viên sủi; hộp 12 viên

**Vì sao sản phẩm xuất hiện:** Sản phẩm xuất hiện khi tìm kiếm từ khóa "thuốc đau đầu" trên Long Châu; hàm lượng 650mg được ghi nhận theo dữ liệu công bố. Hàm lượng cao hơn không đồng nghĩa sản phẩm phù hợp hơn cho bạn.

**Điều cần kiểm tra trước khi dùng:** Hàm lượng cao hơn có thể không phù hợp với cân nặng và tình trạng sức khỏe của bạn; cần hỏi dược sĩ về mức độ phù hợp trước khi dùng.

**Nguồn sản phẩm:** [Xem tại Long Châu](https://nhathuoclongchau.com.vn/hapacol-650mg)

---

### Bảng đối chiếu nhanh

| Tiêu chí | Sản phẩm 1 | Sản phẩm 2 | Sản phẩm 3 | Sản phẩm 4 |
|---|---|---|---|---|
| Thành phần công bố | Paracetamol 500mg | Paracetamol 500mg, cafein 65mg | Paracetamol 500mg | Paracetamol 650mg |
| Dạng bào chế | Viên nén | Viên nén | Viên sủi | Viên sủi |
| Quy cách | Hộp 20 viên | Hộp 20 viên | Hộp 16 viên | Hộp 12 viên |
| Giá tham khảo | 55.000đ | 78.000đ | 92.000đ | 61.000đ |
| Nhóm sản phẩm | Thuốc giảm đau | Thuốc giảm đau | Thuốc giảm đau | Thuốc giảm đau |
| Điểm cần hỏi dược sĩ | Dị ứng, bệnh gan, bệnh thận | Cafein, bệnh tim, giấc ngủ | Natri, bệnh thận | Hàm lượng cao hơn |

### Kết luận an toàn

- Bốn sản phẩm đều ghi nhận hoạt chất công bố là paracetamol với các dạng bào chế và quy cách khác nhau; sự khác biệt đáng chú ý nhất mà dữ liệu hỗ trợ là hàm lượng, dạng viên và thành phần cafein ở sản phẩm thứ hai.
- Mình không chọn thay bạn một sản phẩm cụ thể, đặc biệt khi đây là nhóm cần cân nhắc theo tuổi, cân nặng, bệnh nền và thuốc đang dùng.
- Để đánh giá an toàn chính xác hơn, bạn nên cung cấp thêm thông tin về tuổi, thai kỳ hoặc cho con bú, dị ứng, bệnh nền và danh sách thuốc đang dùng.
- Trước khi sử dụng, hãy đọc nhãn sản phẩm, kiểm tra hạn dùng và xác nhận với bác sĩ hoặc dược sĩ để bảo đảm sản phẩm phù hợp với hoàn cảnh cụ thể của bạn.

### Nguồn và giới hạn dữ liệu

- Knowledge Graph: tên bệnh, warning, consultation need và nguồn tham khảo [WHO Medication Without Harm](https://www.who.int/initiatives/medication-without-harm).
- Long Châu: URL từng sản phẩm được lấy nguyên văn từ kết quả tìm kiếm; thời điểm truy vấn và giá có thể thay đổi.
- Thông tin trong summary chỉ dựa trên dữ liệu tool trả về; mọi chi tiết chưa có trong dữ liệu đều được nêu là cần kiểm tra thêm.
- Thông tin này không thay thế chẩn đoán hoặc đơn thuốc.
"""


def test_final_summary_snapshot_meets_contract() -> None:
    _assert_summary_contract(CANONICAL_SUMMARY)


def test_final_summary_reassembles_from_many_small_chunks() -> None:
    stream = FinalSummaryMarkdownStream()
    chunk_size = 5
    chunks = [
        CANONICAL_SUMMARY[index : index + chunk_size]
        for index in range(0, len(CANONICAL_SUMMARY), chunk_size)
    ]

    output = []
    for chunk in chunks:
        output.extend(stream.feed(chunk))
    output.append(stream.finish())
    reassembled = "".join(output)

    assert reassembled == CANONICAL_SUMMARY
    _assert_summary_contract(reassembled)
