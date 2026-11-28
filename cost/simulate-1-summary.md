# Tóm tắt mô phỏng simulate-1@20261128-092305

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 33 | 1 | 793 | 98 | 1.4 | 2.4 |
| dung_vua | 9 | 2 | 1702 | 220 | 3.1 | 4.9 |
| dung_nhieu | 8 | 2 | 1502 | 181 | 2.6 | 4.2 |

Tỉ lệ đạt dùng để tính: 26/27 (96%) — lượt run-2@20261128-091840

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (999 người) | Chi phí / tháng — cao (3.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash (vào 1.5 · ra 7.5 $/1M) | $0.0026 | $0.0027 | $0.0020 | $1.93 | $6.44 | $19.33 | $0.0064 |
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.00047 | $0.00049 | $0.00036 | $0.3468 | $1.15 | $3.47 | $0.0012 |
| gemini-4-argon (vào 4.0 · ra 20.0 $/1M) | $0.0069 | $0.0072 | $0.0054 | $5.16 | $17.17 | $51.56 | $0.0172 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.3) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gemini-3.8-flash. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
