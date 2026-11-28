# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu — `dung_it` 60% · 1 phiên/tháng · 1 lượt; `dung_vua` 20% · 2 phiên · 2 lượt; `dung_nhieu` 20% · 5 phiên · 2 lượt. Nguồn: tần suất tự báo cáo của P1–P5 (`evidence/summary.md`); số lượt / phiên: *(tự ước tính)*.
- **Số người dùng thật** 3 kịch bản: thấp 300 · cơ sở 999 · cao 3.000. Nguồn: cơ sở = số SV RHM tốt nghiệp năm gần nhất theo Bộ Y tế, dẫn [VnExpress 28/05/2025](https://vnexpress.net/them-mot-truong-dai-hoc-duoc-dao-tao-bac-si-rang-ham-mat-4891698.html); thấp và cao *(tự ước tính)* (30% một khoá; 30% của ~10.000 nha sĩ theo VOSA 2024).
- **Giá** 3 mức model ([`Guide/further-reading/model-prices.md`](../Guide/further-reading/model-prices.md), trang [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), bảng đề ghi xem 25/11/2026), $/1M token vào · ra: `gemini-3.1-flash-lite` (Nhỏ) 0.25 · 1.50 · `gemini-3.8-flash` (Vừa, giá từ 01/01/2027) 1.50 · 7.50 · `gemini-4-argon` (Lớn, giá từ 01/12/2026) 4.00 · 20.00
- **Tỉ lệ đạt** dùng để tính: 26/27 (96%) — lượt `run-2@20261128-091840` (lượt 2)
- Đo token trên model `gemini-3.8-flash` (thinking low), tính giá model `gemini-3.8-flash`, `gemini-3.1-flash-lite` và `gemini-4-argon` (model khác bộ tách token nên số token thật có thể lệch).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-092305` · 50 phiên (0 phiên lỗi) · seed 42 · chạy trên commit `555cbc7` (bản lượt 2)

*(chép nguyên từ `cost/simulate-1-summary.md`)*

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 33 | 1 | 793 | 98 | 1.4 | 2.4 |
| dung_vua | 9 | 2 | 1702 | 220 | 3.1 | 4.9 |
| dung_nhieu | 8 | 2 | 1502 | 181 | 2.6 | 4.2 |

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (999 người) | Chi phí / tháng — cao (3.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash (vào 1.5 · ra 7.5 $/1M) | $0.0026 | $0.0027 | $0.0020 | $1.93 | $6.44 | $19.33 | $0.0064 |
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.00047 | $0.00049 | $0.00036 | $0.3468 | $1.15 | $3.47 | $0.0012 |
| gemini-4-argon (vào 4.0 · ra 20.0 $/1M) | $0.0069 | $0.0072 | $0.0054 | $5.16 | $17.17 | $51.56 | $0.0172 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): **UNKNOWN** — §2 chưa đo được số BS thực sự gặp vấn đề, tần suất đại diện hay số phút tra thuốc riêng. Dữ kiện có: P2, P3 tự báo cáo 2 và khoảng 5 lần phải dừng rà trong tháng; ca gần nhất xử lý khoảng 90 phút (P2) và 3 phút (P3) — là thời gian xử lý ca, không phải thời gian tra thuốc.
- Chi phí / người / tháng (cơ sở, model `gemini-3.8-flash`): **$0.0064** (chỉ tiền model; cả 999 BS ≈ $6.44 / tháng).
- **Kết luận một dòng — đáng làm không:** chi phí model (~$0.006 / BS / tháng, kể cả model Lớn chỉ ~$0.017) không phải rào cản; có đáng làm hay không phụ thuộc impact §2 hiện còn **UNKNOWN** — cần đo số phút tra thuốc tiết kiệm được mỗi ca trước khi kết luận. *(Chưa tính chi phí ngoài model: hosting bot, giờ công BS RHM duyệt bảng quy tắc.)*

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
