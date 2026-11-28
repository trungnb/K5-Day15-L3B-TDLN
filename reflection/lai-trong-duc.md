# Reflection — Lại Trọng Đức

> Thành viên nhóm `TDLN` (Lớp `L3B` · Track `B` — Y tế) · MSSV `2A202604019`.

1. **Vai trò + phần mình làm (trỏ tới file / commit):**
   - Phụ trách đánh giá (`eval/`), số liệu đào data (`evidence/`) và rà mô phỏng chi phí (`cost/`) trong [TEAMS.md](../TEAMS.md).
   - Hoàn thiện kịch bản 4 lớp chỗ khó [spec.md](../spec.md) §5 (`07dfca9`, PR `#3`), 5 metric [metric_spec.yaml](../eval/metric_spec.yaml) (`dbed5ec`) và phiếu chấm độc lập 5 mẫu CP2 khớp `5/5` với BS Trung tại [cp2-cham-cheo-duc.md](../eval/cp2-cham-cheo-duc.md) (`2a458af`, PR `#8`).
   - Đọc kiểm tay `48/48` câu gốc AloBacsi vào [qa_sample.csv](../evidence/qa_sample.csv) và viết kết quả/giới hạn tại [data-mining.md](../evidence/data-mining.md) (`623e3f7`, PR `#14`); viết script rà tất định [grade.py](../eval/grade.py) (`fc92f29`, PR `#15`), tách [metric_notes.csv](../eval/metric_notes.csv) + [test_grade.py](../eval/test_grade.py) (`6a18686`, PR `#29`) và hoàn thiện mục 6 [eval/README.md](../eval/README.md) (`30d3357`, PR `#34`).
   - Chạy thử `simulate --try`, đối chiếu số liệu [personas.yaml](../cost/personas.yaml) và [cost-estimate.md](../cost/cost-estimate.md) ↔ [simulate-1-summary.md](../cost/simulate-1-summary.md) / [simulate-2-summary.md](../cost/simulate-2-summary.md) ↔ [spec.md](../spec.md) §8, trình bày Trang 5–6 trong [demo-slides.pdf](../demo-slides.pdf) và cập nhật [ai-usage.md](../docs/ai-usage.md) cùng [README.md](../README.md).

2. **AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):**
   - Dùng Antigravity hỗ trợ đối chiếu 3 bảng CSV để soạn nháp `spec.md` §5, `eval/metric_spec.yaml`, `eval/README.md` §6, tải nội dung 48 câu AloBacsi ra file nháp cho mình đọc, và viết script tất định `eval/grade.py` cùng `eval/test_grade.py` (không dùng LLM chấm cột `pass`).
   - Phải sửa câu chữ nháp `spec.md` §5 từ giọng kỹ thuật sang cách BS RHM nhắn ca thật khi khám.
   - Sau review PR `#29`, phải bỏ toàn bộ phần tự đoán từ khoá tiếng Việt (`METRIC_NOTE_CUES`) và nhánh tự đoán câu 1 metric trong `eval/grade.py`, chuyển sang đọc `eval/metric_notes.csv` và giữ dấu `?` khi chưa rõ để không che mờ quyết định của người chấm.
   - Tự mở đọc nguyên văn `48/48` câu AloBacsi, kiểm từng mã `DDI`/`CR` cho `5` mẫu CP2 và rà lại từng ô số liệu chi phí trước khi gộp nhánh.

3. **Một câu thử trượt của nhóm và mình học được gì từ nó:**
   - Chọn **`B11`** (*"Bn rối loạn đông máu trong quá trình nhổ răng"*) ở lượt chạy 1 (`run-1@20261128-085926` trong [eval/report.md](../eval/report.md)): dù đã in đúng mã nguy cơ cao `[CR-016]` và kéo tổng điểm đạt `23/27 (85%)`, bot chỉ nhắc thiếu thuốc định kê mà không hỏi lại ca đang nhổ hay đang chuẩn bị và có chảy máu khó cầm hay không.
   - Việc `B11` và `B12` cùng trượt kéo metric `hoi_lai_khi_thieu` xuống `4/6 (66.67% < 80%)`, khiến cả lượt 1 vẫn **không đạt chuẩn §7** dù tỷ lệ câu qua đã vượt `80%`.
   - Bài học rút ra là trong ngữ cảnh lâm sàng, điểm trung bình cao dễ tạo cảm giác yên tâm giả tạo nếu thiếu chốt chặn theo từng hành vi cốt lõi; chính nhờ khoá đủ 5 ngưỡng đồng thời và phân rã từng câu trượt ở `metric_notes.csv`, nhóm mới sửa trúng lỗi ở `codebase/agent.py` (`555cbc7`) để kéo lượt 2 lên `26/27 (96%)` mà không câu nào tụt điểm.
