# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Script / công thức đếm để trong repo (`evidence/count_qa.py`), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — bỏ tên người hỏi, bỏ chi tiết định danh bệnh nhân, trích tối đa 2 câu mỗi mục, ghi link và ngày xem.

## 1. Cách đếm — viết TRƯỚC khi chạy

- **Data dùng:** Mục Hỏi đáp Răng Hàm Mặt công khai trên trang bệnh viện / nền tảng y khoa công khai Việt Nam (ví dụ Vinmec, Medlatec, YouMed, HelloBacsi — Đức chốt 1–2 URL cụ thể và ngày xem tại `evidence/qa_sample.csv` trước khi chạy).
- **Đếm gì:** Số câu hỏi công khai có nhắc đến **bệnh nền / thuốc đang uống / dị ứng thuốc** gắn với **thủ thuật RHM** (nhổ răng, tiểu phẫu, cắm implant, lấy cao răng/tiêm tê) hoặc **thuốc định dùng trong RHM** (kháng sinh, giảm đau NSAID, corticoid), phân nhãn theo loại yếu tố nguy cơ.
- **Trên tập nào / lọc gì:** Lấy `N` câu hỏi công khai liên tiếp mới nhất trong chuyên mục RHM tại thời điểm thu thập (không lọc bỏ câu bình thường trước khi gán nhãn để tránh lệch mẫu).
- **Mẫu số là gì (`N`):** Tổng số câu hỏi RHM công khai liên tiếp đã đọc và gắn nhãn (kể cả câu không liên quan đến bệnh nền/thuốc nền). Mục tiêu `N ≥ 40` (khuyến nghị 50 câu).
- **Script / công thức:** `evidence/qa_sample.csv` + `evidence/count_qa.py` *(Đức tạo khi chạy)*.

## 2. Đọc trước, đếm sau

Đã đọc __ dòng đầu. Các *kiểu* câu hỏi thấy được (trước khi định nghĩa thứ cần đếm):
- __
- __

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| | | | |
| | | | |

Ghi dạng `x/N (y%)`. *"Nhiều bạn…"* không phải số.

## 4. ≥5 ví dụ cụ thể (mã dòng / link + ngày xem, bỏ tên)

1.
2.
3.
4.
5.

## 5. Giới hạn của data

- Câu hỏi trên mạng là góc nhìn **bệnh nhân tự hỏi** (thường lo lắng trước khi đi làm răng hoặc sau khi đọc đơn), **không phải** log tra cứu nội bộ của bác sĩ RHM.
- Vì vậy nguồn này chỉ dùng làm **nguồn thứ 2 kiểm chéo** với nguồn chính là phỏng vấn ≥3 BS RHM ngoài nhóm: kiểm xem các nhóm bệnh nền/thuốc nền nào gây lo ngại và xuất hiện lặp lại ở cả 2 phía (bệnh nhân hỏi ↔ bác sĩ phải xử lý).
- Thiếu gì, lệch về phía nào thêm sau khi chạy: __
→ Kiểm lại bằng phỏng vấn: `evidence/interviews/P1.md`… (`evidence/summary.md`).
