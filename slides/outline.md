# Dàn slide → lấy số từ file nào

> Làm ở guide bước 5.1. Luật: **không có bằng chứng thì không có slide** — mỗi trang ≥1 con số / trích dẫn có nguồn / kết quả đo.
> Xuất PDF thành `demo-slides.pdf` ở thư mục gốc repo, nộp tại CP4 14:30 Thứ Bảy 28/11. Định dạng nào cũng được (PDF, PPTX, HTML…); hoặc nộp link slide (Drive, Canva, Google Slides…) ở form CP4, để ai có link cũng xem được.

| # | Trang | Có gì | Số lấy từ | Xong |
|---|---|---|---|---|
| 1 | Người dùng & pain | BS RHM ngoại trú · rà soát bệnh nền/thuốc nền/dị ứng × thủ thuật & đơn RHM · số liệu 5 BS (P1–P5), 9 trích dẫn + đối chiếu nguồn hỏi đáp | `evidence/summary.md`, `evidence/data-mining.md` | ☐ |
| 2 | Vì sao chọn bài này | Bảng impact rút gọn (999 BS RHM tốt nghiệp/năm theo Bộ Y tế; ~10.000 nha sĩ VOSA 2024; tần suất P1–P5; hướng B2-BN & B3-Nhà thuốc đã loại) | `spec.md` §2, `cost/personas.yaml` | ☐ |
| 3 | Giải pháp | Lát cắt 1 câu · sơ đồ workflow cố định 5 bước + 3 lớp chặn sót `HIGH` · AI gợi ý, BS quyết định | `spec.md` §4, `docs/design.md` | ☐ |
| 4 | Demo live | 1 ca thường (`B01` hoặc `B08`) + 1 ca khó thuốc phối hợp (`B10`/`B17`) trên Bot Zalo 24/24; dự phòng `python3 run.py` + video | `eval/benchmark.csv`, `bot/zalo_bot.py` | ☐ |
| 5 | **Đánh giá thế nào** | 3 bảng CSV v1.1 · 27 câu (9/27 nguồn thật) · 5 metric · chấm chéo 5/5 · lượt 1 → lượt 2 so với chuẩn đạt (≥22/27) · lỗi chính | `eval/README.md`, `eval/report.md` | ☐ |
| 6 | **Chi phí khi dùng thật** | Chi phí / task thành công (`gemini-3.8-flash` chính, so với `gemini-3.1-flash-lite`) · 3 kịch bản (300 / 999 BS mới tốt nghiệp/năm / 3.000 BS) · so sánh với thời gian tiết kiệm | `cost/cost-estimate.md` | ☐ |
| 7 | Kết luận | Go / iterate / stop — dẫn số thực từ trang 1, 5, 6 | — | ☐ |
| 8 | Nếu có thêm 1 tuần | Phủ thêm thuốc phổ biến ngoài bảng (spiramycin, esomeprazole…), nối kiểm liều ở output, tăng log thử nghiệm BS | `eval/report.md` mục 4 · `validation/log.md` · `docs/design.md` §11 | ☐ |

**Trước khi lên:** tải repo về một máy khác (hoặc thư mục mới), chạy theo mục "Chạy trong 3 phút" của `README.md` · `.env` có trên máy demo (hoặc bot VM chạy sẵn), đã gọi thử 1 câu trong vòng 1 giờ trước giờ demo · video dự phòng mở được bằng cửa sổ ẩn danh · biết bản chạy thử sẽ làm gì với **1 câu thử lạ** của giám khảo.

Ai nói trang nào (dự kiến theo `docs/team-plan.md` §C — cả nhóm rà chốt trước CP4):

| Trang | Người nói |
|---|---|
| 1, 2, 7 | Trung *(pain, bằng chứng lâm sàng & kết luận)* |
| 3, 4 | Lĩnh *(kiến trúc workflow 5 bước & demo live)* |
| 5, 6 | Đức *(eval lượt 1 → lượt 2 & mô phỏng chi phí)* |
| 8 (+ điều phối slide) | Nguyên *(hướng phát triển, phản hồi bot Zalo & xuất `demo-slides.pdf`)* |
