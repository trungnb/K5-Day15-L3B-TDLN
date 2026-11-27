# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Thiết kế luồng xử lý & tài liệu thiết kế | Claude Code (Claude Opus 5.5) | Đọc repo, đề xuất luồng 5 bước, soạn `docs/design.md` (schema JSON, luật từng bước, câu chữ cố định, xử lý lỗi), `spec.md` §4 §9, sơ đồ Mermaid, cập nhật `team-plan.md` §B; đối chiếu thiết kế với 3 file CSV và `eval/benchmark.csv` để tìm chỗ hở (thuốc phối hợp, "dị ứng ibuprofen", thiếu thông tin) | Lĩnh duyệt từng quyết định trước khi commit và bác một số đề xuất (vd không thêm trường JSON cho thuốc không rõ vai, chỉ hỏi lại); câu chữ cố định do Trung duyệt | Lĩnh |
| Code bản chạy thử | | | | |
| Prompt / thiết kế lời gọi mô hình | | | | |
| Đào data (viết script đếm, gợi ý nhãn) | Claude Code (Claude Opus 5.5) | Viết `evidence/crawl_qa.py` (gom 48 câu hỏi đáp RHM công khai trên AloBacsi) và `evidence/count_qa.py`; gán nhãn nháp 48 dòng `evidence/qa_sample.csv` (cột `nguoi_gan_nhan` = `AI-nhap`) | Nguyên kiểm tay 15 dòng, khớp 15; Đức đọc kiểm tay toàn bộ 48/48 câu hỏi gốc, khớp 48/48 nhãn nháp và đổi cột `nguoi_gan_nhan` thành `Nguyen, Duc` | Nguyên & Đức |
| Rà câu hỏi phỏng vấn / khảo sát | | Chỉ rà câu dẫn dắt | | |
| Viết câu thử (benchmark) | | | Mỗi câu thử có `source`; câu thử AI viết được ghi rõ | |
| Sinh data `synthetic` (nếu có) | | | Seed __ · kiểm tay __ dòng | |
| Chấm cột `pass` bằng LLM (nếu có) | | | Kiểm tra thủ công __ câu thử, khớp __/__ | |
| Slide, văn bản | Claude Code (Claude Opus 5.5) | Tìm và đọc nguồn, soạn nháp `spec.md` §2 (quy mô BS RHM) và §3 (giải pháp tương tự), soạn `README.md` | Nguyên đọc lại từng nguồn trích và số liệu; nguồn trang gốc §3 chưa mở được bằng công cụ, cần mở lại bằng trình duyệt | Nguyên |
| Dữ liệu `data/build/` (luật thuốc phối hợp) | Claude Code (Claude Opus 5.5) | Viết `expand_combo_rows()` và luật `combo:` trong `validate_csv.py`, tách 4 dòng alias | Chạy validator trước/sau + 7 trường hợp kiểm; Trung duyệt thành phần thuốc phối hợp | Nguyên (Trung duyệt) |
| Đặc tả đánh giá (`spec.md` §5, `eval/metric_spec.yaml`) & phiếu chấm chéo CP2 | Antigravity (Gemini 4 Carbon) | Đối chiếu 3 bảng CSV với luồng thiết kế để soạn nháp kịch bản chỗ khó (`spec.md` §5), 5 metric (`eval/metric_spec.yaml`) và bảng rà tiêu chí cho `eval/cp2-cham-cheo-duc.md` | Đức kiểm lại từng mã `DDI`/`CR`, chỉnh câu chữ dễ hiểu, tự duyệt kết luận từng câu trong 5 output chấm chéo (khớp 5/5 với BS Trung) và chạy `python run.py check` | Đức |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
