from app.medication.skill_loader import load_medication_skill


def test_skill_has_no_adk_session_template_placeholders() -> None:
    instruction = load_medication_skill()

    assert "{productUrl}" not in instruction
    assert "{imageUrl}" not in instruction
    assert "{price}" not in instruction


def test_skill_contains_final_summary_contract_and_medication_guardrails() -> None:
    instruction = load_medication_skill()

    required_sections = [
        "### Tóm tắt nhu cầu của bạn",
        "### Cảnh báo cần ưu tiên",
        "### Các sản phẩm được tìm thấy để tham khảo",
        "### Bảng đối chiếu nhanh",
        "### Kết luận an toàn",
        "### Nguồn và giới hạn dữ liệu",
    ]
    positions = [instruction.index(section) for section in required_sections]

    assert positions == sorted(positions)
    assert "deepseek-v4-flash" in instruction
    assert "không chẩn đoán" in instruction.lower()
    assert "không kê đơn" in instruction.lower()
    assert "500" in instruction and "900 từ" in instruction
    assert "600" in instruction and "800 từ" in instruction
    assert "FOMO" in instruction
