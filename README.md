# Medication Consultation Agent

FastAPI service dùng Google Agent Development Kit (ADK) để quản lý agent,
runner, tool và session. Agent hiện dùng Gemini qua Google ADK, kết hợp Neo4j
và dữ liệu Long Châu để tạo câu trả lời tư vấn thuốc có grounding.

## Kiến trúc

```text
POST /chat
  -> ChatRuntime + ADK Runner + SQLite session history
  -> Gemini 3.1 Flash Lite
  -> consult_medication(condition, product_keyword)
  -> MedicationConsultationService
       |-> Neo4jMedicationRepository (warning + consultation need)
       `-> LongChauClient (normalized product search)
  -> SSE text chunks + done + [DONE]
```

`MedicationConsultationService.consult(...)` là interface nghiệp vụ chính.
Route không chứa prompt, Cypher hoặc HTTP logic. Neo4j và Long Châu là các
adapter độc lập qua Protocol nên có thể kiểm thử bằng fake mà không gọi mạng.

## Cấu hình

Sao chép `.env.example` thành `.env`, sau đó điền các biến bắt buộc:

```dotenv
GOOGLE_API_KEY=...
NEO4J_URI=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j
SESSION_DB_URL=sqlite+aiosqlite:///./data/adk_sessions.db
```

`src/app/agent.py` hiện dùng Gemini (`gemini-3.1-flash-lite`) nên cần `GOOGLE_API_KEY`
lấy từ https://aistudio.google.com/apikey. Ứng dụng dừng ngay khi khởi động nếu
thiếu cấu hình Gemini/Neo4j.

## Chạy local

```powershell
uv sync --all-groups
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/docs`.

## Chat SSE

```http
POST /chat
Content-Type: application/json

{
  "message": "Tôi bị đau đầu nên tham khảo thuốc gì?",
  "sessionId": null,
  "userId": "guest"
}
```

Response là `text/event-stream`:

```text
data: {"type":"progress","statusText":"Đang tra cứu Knowledge Graph...","progressPercent":20,"sessionId":"..."}

data: {"type":"message","content":"...","sessionId":"...","phase":"FINAL_SUMMARY"}

data: {"type":"done","sessionId":"..."}

data: [DONE]
```

Chỉ text cuối được phát ra. Tool call, tool response và model thinking bị lọc.
Các chunk `progress` (5% -> 96%) báo từng giai đoạn xử lý: phân tích câu hỏi,
tra cứu Knowledge Graph, tìm sản phẩm Long Châu, đối chiếu an toàn và viết từng
section của báo cáo. `sessionId` mới là UUID; session cũ chỉ được tiếp tục bởi
cùng `userId`. ADK lưu history và state `final_summary` trong SQLite.

## Endpoint tương thích hệ thống cũ

- `POST /diabetes/v1/predict`
- `POST /housing/v1/predict`
- `GET /hi`

Request fields, mã lỗi HTTP 400 và JSON response của hai prediction endpoint
được giữ nguyên từ Flask service cũ, nhưng model chỉ được lazy-load khi gọi.

## Quality gate

```powershell
uv run pytest -q
uv run ruff check src tests main.py scripts
uv run python -c "import main; print(main.app.title)"
```

Các test bao phủ model ID, cấm Google model credentials, Neo4j query
parameterization/read routing, Long Châu normalization/error, source degradation,
session ownership, SSE sanitization/disconnect và regression prediction routes.

## Giới hạn an toàn

Skill tại `resources/skills/medication_consultation/SKILL.md` buộc agent dùng dữ liệu từ
tool cho phát biểu cụ thể, không chẩn đoán/kê đơn/tự tạo liều, không dùng FOMO
hoặc ngôn ngữ chốt sale. Dữ liệu Long Châu chỉ là sản phẩm tham khảo; giá và
trạng thái có thể thay đổi.
