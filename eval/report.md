# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-085926` | 23/27 | 85% | 2/2 | 14/18 | 7/7 | chưa (hỏi lại đúng 4/6 = 67% < 80%) |
| 2 | `run-2@20261128-091840` | 26/27 | 96% | 2/2 | 17/18 | 7/7 | đạt (hỏi lại đúng 6/6; HIGH 9/9; từ chối 7/7) |

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

- Nhắm vào nhóm lỗi: **không chỉ rõ phần còn thiếu** (gộp hai nhóm ở §2: B11, B12, B15 không hỏi lại; B13 không nói bảng chưa có quy tắc). Vì sao đau nhất: BS nhận tin trả lời không có câu hỏi hay giới hạn rõ thì dễ hiểu là "đã kiểm đủ"; đây cũng là metric duy nhất dưới ngưỡng ở lượt 1 (hỏi lại đúng 4/6 = 67% < 80%). P2, P3 kể ca phải hỏi thêm trước thủ thuật (`evidence/summary.md`).
- Đã sửa gì (một lần, chỉ `codebase/agent.py`, commit `555cbc7`; không đổi `data/*.csv`, bộ câu thử, chuẩn "đạt"; phát hiện bằng so khớp chữ đã chuẩn hoá, không thêm lần gọi model):
  - Q7: tin nói đang nhổ / đang chảy máu và thủ thuật thuộc nhóm chảy máu → hỏi giai đoạn và chảy máu khó cầm (B11).
  - Q6: bệnh nền model đọc được mà bảng không có → hỏi tên bệnh và tình trạng hiện tại (B12).
  - ℹ️ cặp thuốc: đã nhận ra thuốc mà cả ca không khớp rule DDI nào → nêu cặp chưa có quy tắc (B13).
  - ℹ️ tác dụng phụ: tin hỏi "tác dụng phụ" → nêu giới hạn tra cứu (B15).
  - Kiểm: 13 test offline `codebase/test_agent_hoi_lai.py` (đỏ trước, xanh sau); review độc lập 1 vòng, đã sửa 3 lỗi P2 (cụm "trong quá trình" quá rộng, ✅ in cùng Q7, câu phủ định) và 1 P3.
- Kết quả: nhóm lỗi đó 0/4 → 3/4 (B11, B12, B15 qua; B13 còn trượt) · tổng 85% → 96% · hỏi lại đúng 4/6 → 6/6.
- Câu nào **tệ đi** sau khi sửa: không câu nào đổi từ đạt sang trượt. 13/27 câu có output trùng nguyên văn lượt 1; các câu còn lại đổi chữ do model lần 2 viết lại khác. Thêm nhiễu: B15 bị model gắn thêm 🚫 `khac`; B13, B14 dòng ❔ liệt kê thêm cụm không phải thuốc/bệnh ("giảm đau", "đau răng về đem liên tục").

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào:
  - B13: chưa ưu tiên "BS đánh giá trực tiếp sớm" cho ca cấp (viêm mô tế bào) — hệ thống không nhận ra mức cấp của bệnh cảnh, BS có thể chậm chuyển khám.
  - B14: "ibu" chưa nhận ra là ibuprofen (thiếu alias; `data/*.csv` đã chốt từ trước `run-1` nên không sửa trong lượt 2) — nếu BN đang dùng thuốc chống đông, cảnh báo NSAID có thể bị sót.
  - Phát hiện Q7 / ℹ️ dựa vào cụm chữ cố định → cách viết khác ("đang can thiệp", "tác dụng không mong muốn") chưa bắt được.
  - Chưa tách bộ held-out: 4 câu nhắm sửa nằm trong cùng bộ 27 câu, nên 96% có thể lạc quan.
- Nếu có thêm 1 tuần: bổ sung alias viết tắt BS hay dùng (ibu, para…) có BS RHM duyệt; tách ~20% câu held-out; thêm câu thử cho các cách viết khác của Q6/Q7; nhận diện ca cấp (nhiễm trùng lan toả) để nhắc chuyển khám sớm.
