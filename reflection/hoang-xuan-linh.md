# Reflection — Hoàng Xuân Lĩnh

> Thành viên nhóm `TDLN` (Lớp `L3B` · Track `B` — Y tế) · Mã học viên `2A202604017`.

1. **Vai trò + phần mình làm (trỏ tới file / commit):**
   - Phụ trách AI core trong [TEAMS.md](../TEAMS.md): thiết kế luồng xử lý và code `codebase/agent.py`, `tools.py`, `ai.py`.
   - Thiết kế workflow cố định 5 bước, tối đa 2 lần gọi model, ba lớp chặn sót cảnh báo `HIGH` tại [docs/design.md](../docs/design.md), [spec.md](../spec.md) §4 và §9, cập nhật `docs/team-plan.md` §B (`05944ed` PR `#7`, `db9367f` PR `#10`).
   - Viết luồng thật thay bản tạm CP2: chuẩn hoá alias nhiều dòng, tra 2 bảng quy tắc, model 2 viết từng dòng và code kiểm từng dòng, nối `gemini-3.8-flash` (`5d8b0c6`, PR `#16`); chọn `MODEL_THINKING=low` sau khi đo thấy token ra giảm khoảng 10 lần mà vẫn đúng mã (`0a2d0ce`).
   - Chạy thử 27 câu với model thật trước `run-1` rồi sửa: từ đệm "nhổ một răng" (B01), câu phủ định (B22, `b9ea4ba`), luật hỏi gây tê Q5 (`051b6cc`), không tự gán vai thuốc và 3 loại từ chối cụ thể (`09c6f48`). Trình bày trang 3–4 (kiến trúc, demo) ở CP4.

2. **AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):**
   - Dùng Claude Code (Claude Opus 5.5) để đọc repo, đề xuất thiết kế, viết code, chạy thử trên model thật và soạn PR; mình quyết định từng thay đổi trước khi commit.
   - Bác đề xuất thêm một trường JSON cho "thuốc không rõ vai" (B08) vì làm luồng phức tạp; chọn cách đơn giản hơn là xếp vào thuốc đang dùng và hỏi lại Q1.
   - Hỏi lại khi AI tự bỏ cờ "thiếu thông tin" của model 1 và chỉ đồng ý sau khi hiểu lý do (code tự xác định thiếu thủ thuật / thuốc định kê thì chắc hơn); giữ nguyên tắc không gộp vào `main` trước CP2 19:30 và không sửa file của bạn khác ngoài PR.
   - Tự kiểm cấu hình `.env` (key dán nhầm loại khác nhà cung cấp) và đọc output thật của từng câu thử thay vì tin vào tóm tắt của AI.

3. **Một câu thử trượt của nhóm và mình học được gì từ nó:**
   - Chọn **`B22`** (*"BN có tiền sử dị ứng thuốc tê tại chỗ. Kế hoạch là lấy cao dưới nướu, chưa ghi có gây tê hay không."*): ở lượt thử `eval --try 27` ngày 27/11, bước code quét lại tin gốc thấy chữ "gây tê" nên coi như đã có gây tê và báo `[CR-010]` như đã xác nhận — đúng điều `pass_criterion` ghi là trượt.
   - Nguyên nhân: lớp bảo hiểm quét chữ được thêm để không sót thuốc, nhưng nó không hiểu câu phủ định ("chưa ghi có gây tê"). Sửa: khi model đọc được tin thì quét lại chỉ bổ sung thuốc, còn bệnh nền / dị ứng / thủ thuật tin theo model; thêm Q5 hỏi "có dự kiến gây tê không". `B22` đạt ở cả `run-1` và `run-2`.
   - Bài học: một lớp an toàn tất định cũng có thể tạo lỗi nếu phạm vi quá rộng — mỗi lớp chặn cần đúng phạm vi rủi ro nó bảo vệ (ở đây là sót thuốc). Và nên chạy thử trên model thật trước lượt chính thức, vì lỗi kiểu này không lộ ra ở chế độ model giả.
