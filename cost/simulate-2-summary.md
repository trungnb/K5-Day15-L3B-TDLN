# Tóm tắt mô phỏng simulate-2@20261128-151610

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 33 | 1 | 912 | 91 | 1.5 | 2.6 |
| dung_vua | 9 | 2 | 2072 | 207 | 3.4 | 5.3 |
| dung_nhieu | 8 | 2 | 1759 | 174 | 2.8 | 5.0 |

Tỉ lệ đạt dùng để tính: 26/27 (96%) — lượt run-2@20261128-091840

- Tự chọn: lượt run-N mới nhất đã chấm xong, chạy bằng đúng model đang đo (run-2.csv). Muốn dùng lượt khác (vd lượt 2): thêm `--rate-from eval/run-2.csv`.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (999 người) | Chi phí / tháng — cao (3.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.8-flash (vào 1.5 · ra 7.5 $/1M) | $0.0028 | $0.0029 | $0.0022 | $63.36 | $211.00 | $633.63 | $0.2112 |
| gemini-3.1-flash-lite (vào 0.25 · ra 1.5 $/1M) | $0.00050 | $0.00052 | $0.00039 | $11.26 | $37.50 | $112.62 | $0.0375 |
| gemini-4-argon (vào 4.0 · ra 20.0 $/1M) | $0.0075 | $0.0078 | $0.0058 | $168.97 | $562.66 | $1,689.68 | $0.5632 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.3) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gemini-3.8-flash. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
