# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-085926` | 23/27 | 85% | 2/2 | 14/18 | 7/7 | chưa (hỏi lại đúng 4/6 = 67% < 80%) |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Không hỏi lại dữ kiện còn thiếu dù đã nhận đủ thực thể | 3 | B11, B12, B15 |
| Không nói rõ bảng chưa có quy tắc cho cặp thuốc đã nhận ra | 1 | B13 |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B11 | "Bn rối loạn đông máu trong quá trình nhổ răng" | Có `[CR-016]` HIGH, rồi nhắc thiếu thuốc định kê | Không hỏi ca đang nhổ hay đang chuẩn bị, có chảy máu khó cầm không |
| B12 | "Bn th áp đang điều trị cần nhổ răng" | `❔ Chưa có dữ liệu cho: th áp đang điều trị` | Không hỏi mức kiểm soát nếu là tăng huyết áp |
| B13 | Viêm mô tế bào, para + azithro | Nhận ra paracetamol, azithromycin; `❔` cho "viêm mô tế bào má phải" | Không nói bảng chưa có quy tắc cho cặp này, không hướng BS đánh giá sớm |
| B15 | "Tac dung phu/ chong chi dinh Methylpred 16, metronidazol 500, amox 500" | Hỏi Q1 vai trò thuốc | Không nêu giới hạn với câu hỏi tác dụng phụ chung |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: __
- Nếu có thêm 1 tuần: __
