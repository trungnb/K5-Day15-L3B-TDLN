# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu — `dung_it` 60% · 1 lần/ngày (30 phiên/tháng) · 1 lượt; `dung_vua` 20% · 2 lần/ngày (60 phiên) · 2 lượt; `dung_nhieu` 20% · 5 lần/ngày (150 phiên) · 2 lượt → trung bình 60 phiên / BS / tháng. Tần suất theo ngày: *(tự ước tính, Trung chốt 28/11)* — cao hơn ~30 lần tần suất P1–P5 tự báo cáo (1–5 ca phải dừng rà / tháng, `evidence/summary.md`), tức giả định BS tra cả ca thường chứ không chỉ ca khó. Số lượt / phiên: *(tự ước tính)*.
- **Số người dùng thật** 3 kịch bản: thấp 300 · cơ sở 999 · cao 3.000. Nguồn: cơ sở = số SV RHM tốt nghiệp năm gần nhất theo Bộ Y tế, dẫn [VnExpress 28/05/2025](https://vnexpress.net/them-mot-truong-dai-hoc-duoc-dao-tao-bac-si-rang-ham-mat-4891698.html); thấp và cao *(tự ước tính)* (30% một khoá; 30% của ~10.000 nha sĩ theo VOSA 2024).
- **Giá** 3 mức model ([`Guide/further-reading/model-prices.md`](../Guide/further-reading/model-prices.md), trang [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), bảng đề ghi xem 25/11/2026), $/1M token vào · ra: `gemini-3.1-flash-lite` (Nhỏ) 0.25 · 1.50 · `gemini-3.8-flash` (Vừa, giá từ 01/01/2027) 1.50 · 7.50 · `gemini-4-argon` (Lớn, giá từ 01/12/2026) 4.00 · 20.00
- **Tỉ lệ đạt** dùng để tính: 26/27 (96%) — lượt `run-2@20261128-091840` (lượt 2, đo trên code `555cbc7`; agent đã sửa sau đó, chưa chạy lượt chấm mới)
- Đo token trên model `gemini-3.8-flash` (thinking low), tính giá model `gemini-3.8-flash`, `gemini-3.1-flash-lite` và `gemini-4-argon` (model khác bộ tách token nên số token thật có thể lệch).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-2.csv` · run ID `simulate-2@20261128-151610` · 50 phiên (0 phiên lỗi) · seed 42 · chạy trên commit `b1c569a` + `cost/personas.yaml` theo ngày. Bản trước (`simulate-1`, 1 / 2 / 5 phiên/tháng, commit `555cbc7`): $0.0064 / BS / tháng.

*(chép nguyên từ `cost/simulate-2-summary.md`)*

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 33 | 1 | 912 | 91 | 1.5 | 2.6 |
| dung_vua | 9 | 2 | 2072 | 207 | 3.4 | 5.3 |
| dung_nhieu | 8 | 2 | 1759 | 174 | 2.8 | 5.0 |

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (999 người) | Chi phí / tháng — cao (3.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash (vào 1.5 · ra 7.5 $/1M) | $0.0028 | $0.0029 | $0.0022 | $63.36 | $211.00 | $633.63 | $0.2112 |
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.00050 | $0.00052 | $0.00039 | $11.26 | $37.50 | $112.62 | $0.0375 |
| gemini-4-argon (vào 4.0 · ra 20.0 $/1M) | $0.0075 | $0.0078 | $0.0058 | $168.97 | $562.66 | $1,689.68 | $0.5632 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): **ước tính ~3 giờ BS / tháng** = 60 phiên (trung bình persona) × 3 phút (giả định, chưa đo); cả 999 BS ≈ 3.000 giờ / tháng. Cả hai số đều dựa trên tần suất *(tự ước tính)* ở §1 — nếu BS chỉ dùng cho ca khó như phỏng vấn báo (1–5 lần/tháng) thì chi phí và impact cùng giảm ~30 lần, tỉ lệ giữa chúng không đổi. Số đo thật vẫn **UNKNOWN** — §2 chưa đo được số BS thực sự gặp vấn đề, tần suất đại diện hay số phút tra thuốc riêng. Dữ kiện có: P2, P3 tự báo cáo 2 và khoảng 5 lần phải dừng rà trong tháng; ca gần nhất xử lý khoảng 90 phút (P2) và 3 phút (P3) — là thời gian xử lý ca, không phải thời gian tra thuốc.
- Chi phí / người / tháng (cơ sở, model `gemini-3.8-flash`): **$0.2112** (chỉ tiền model; cả 999 BS ≈ $211.00 / tháng).
- **Kết luận một dòng — đáng làm không:** chi phí model (~$0.21 / BS / tháng, model Lớn ~$0.56) không phải rào cản; so với ước tính ~3.000 giờ BS / tháng (giả định §2) thì đáng làm tiếp, nhưng impact và tần suất dùng chưa đo — cần đo số lần dùng thật và số phút tra thuốc tiết kiệm được mỗi ca trước khi dùng thật (*iterate*). *(Chưa tính chi phí ngoài model: hosting bot, giờ công BS RHM duyệt bảng quy tắc.)*

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm
