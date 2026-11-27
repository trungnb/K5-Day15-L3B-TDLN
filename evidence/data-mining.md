# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Script / công thức đếm để trong repo (`evidence/count_qa.py`), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — bỏ tên người hỏi, bỏ chi tiết định danh bệnh nhân, trích tối đa 2 câu mỗi mục, ghi link và ngày xem.

## 1. Cách đếm — viết TRƯỚC khi chạy

- **Nguồn:** Trang đầu của hai mục AloBacsi [Nha khoa](https://alobacsi.com/kham-benh-online/nha-khoa) và [Răng Hàm Mặt](https://alobacsi.com/kham-benh-online/rang-ham-mat), xem ngày 27/11/2026.
- **Lấy mẫu:** Lấy các bài hiển thị trên trang đầu của từng mục, gộp theo URL và bỏ trùng. Script chỉ giữ bài đọc được dữ liệu câu hỏi và ngày đăng. Bộ cố định có 48 URL duy nhất, đăng từ 27/05/2025 đến 26/11/2026. Đây là mẫu theo hai trang danh mục; không suy rộng thành các bài mới nhất trên toàn trang.
- **Mẫu số:** N = 48 gồm cả dòng âm tính. CSV giữ mã, URL, ngày và nhãn nháp để Đức rà; mở link gốc khi cần kiểm. Chỉ đưa các trích dẫn đã chọn và bỏ định danh vào phần ví dụ.
- **Tử số chính:** Câu có bệnh nền, thuốc nền hoặc dị ứng gắn với thủ thuật hoặc thuốc RHM. Mang thai/cho bú báo riêng. Mỗi nhãn chỉ đếm một lần trên một câu.
- **Chạy lại:** python3 evidence/count_qa.py. Đức rà toàn bộ nhãn trước khi điền kết quả và ghi số kiểm tay vào docs/ai-usage.md.

## 2. Đọc trước, đếm sau

Rà tay toàn bộ nhãn: UNVERIFIED, chờ Đức ghi nhận.

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Bệnh nền, thuốc nền hoặc dị ứng gắn với thủ thuật/thuốc RHM | UNVERIFIED / 48 | UNVERIFIED | Chờ Đức rà nhãn |

Ghi dạng `x/N (y%)`. *"Nhiều bạn…"* không phải số.

## 4. ≥5 ví dụ cụ thể (mã dòng / link + ngày xem, bỏ tên)

Chờ Đức chọn 5 ví dụ sau khi rà nhãn. Phân biệt ví dụ dương tính, âm tính và giáp ranh.

## 5. Giới hạn của data

- Câu hỏi trên mạng là góc nhìn **bệnh nhân tự hỏi** (thường lo lắng trước khi đi làm răng hoặc sau khi đọc đơn), **không phải** log tra cứu nội bộ của bác sĩ RHM.
- Vì vậy nguồn này chỉ dùng làm **nguồn thứ 2 kiểm chéo** với nguồn chính là phỏng vấn ≥3 BS RHM ngoài nhóm: kiểm xem các nhóm bệnh nền/thuốc nền nào gây lo ngại và xuất hiện lặp lại ở cả 2 phía (bệnh nhân hỏi ↔ bác sĩ phải xử lý).
- Thiếu gì, lệch về phía nào thêm sau khi chạy: __
→ Kiểm lại bằng phỏng vấn: `evidence/interviews/P1.md`… (`evidence/summary.md`).
