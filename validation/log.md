# Người dùng thử *(bonus)*

> Điền ở guide bước 4.3 — 2–3 người ngoài nhóm, ~10 phút / người, theo 5 nhịp: làm quen · bối cảnh · giao việc · quan sát · hỏi sau. Ôn lại: ngày 5, ngày 13. Chấm ở rubric Bonus.
> Không ghi tên: ghi vai. Hành vi quan sát được nặng hơn lời nói; toàn lời khen = phiên chưa đạt, giao việc khó hơn.
> Người dùng thử **không thay được** bằng chứng pain ở `evidence/`.

| Người thử (vai) | Việc giao (theo kết quả, không theo nút) | Quan sát (làm gì đầu tiên, chỗ do dự, chỗ hiểu sai) | Trích nguyên văn | Mức nghiêm trọng (cao / vừa / thấp) |
|---|---|---|---|---|
| BS ngoài nhóm 1¹ (Zalo, chat `0f9e…`) | UNKNOWN — chờ Nguyên ghi việc đã giao | 12:24:36 gửi ngay 1 ca đủ dữ kiện, trùng nguyên văn kịch bản demo của nhóm. Bot trả 3 nguy cơ cao, 2 cần thận trọng, 1 mục chưa có dữ liệu. 18 giây sau nhắn "chi tiết": bot (bản trước deploy 12:29) gửi lại **toàn bộ** tin cũ thay vì phần chi tiết. Không nhắn thêm. | "BN nam 68t, tăng huyết áp đang ổn định, dị ứng penicillin, đang uống warfarin. Dự kiến nhổ R48 mọc lệch. Định kê Augmentin + Alaxan." · "chi tiết" | vừa² — đã sửa (PR #43) |
| BS ngoài nhóm 2¹ (Zalo, chat `7b91…`) | UNKNOWN — chờ Nguyên ghi việc đã giao | 12:26:03 việc đầu tiên: gõ "Huongdan" (không dấu, không "/"). Bot coi là yêu cầu ngoài phạm vi (🚫) thay vì mở hướng dẫn. | "Huongdan" | vừa² — đang sửa ở branch `fix/huongdan-tha-on-dinh` (chưa merge) |
| BS ngoài nhóm 2¹ (tiếp) | như trên | 12:28:50 (2 phút 47 giây sau) gửi 1 ca nội nha R16. Bot nhận ra thủ thuật, lidocain, paracetamol; **không** nhận ra "amlodipin", "vigentin"³, "cao huyết áp" → nói "chưa có dữ liệu… nên không đoán", không ra ✅. Không nhắn thêm. | "Bn 65t sử dụng amlodipin  cao huyết áp. Dự kiến điều trị tuỷ r16 gây tê bằng lidocain. Kê đơn: vigentin + paracetamol" | cao² — thiếu thuốc nền và kháng sinh thì bot không rà được tương tác/dị ứng. Đã thêm alias vigentin, amlodipin và `DDI-037`/`DDI-038` (chưa deploy); "cao huyết áp" không kèm tình trạng vẫn được hỏi lại |

¹ Nguồn: log bot trên VM `bot/logs/20261128.jsonl`. Nhóm xác định chat bắt đầu 27/11 là của nhóm, chat bắt đầu 28/11 là người ngoài; vai "BS" theo lịch buổi thử 11:30–13:00, chưa xác nhận từng người. Giờ ICT. Cả 4 lượt diễn ra **trước** deploy 12:29. Không có ghi chép quan sát trực tiếp: cột quan sát chỉ ghi hành vi thấy trong log, không ghi chỗ do dự hay hiểu sai.
² Mức nghiêm trọng là đề xuất của nhóm từ log, chưa có người thử xác nhận.
³ Vigentin là biệt dược amoxicillin + acid clavulanic (Trung — BS RHM — yêu cầu thêm alias 28/11/2026).

Câu hỏi sau: *"Nếu mai không được dùng nữa, bạn thấy: rất tiếc / hơi tiếc / không sao?"* → UNKNOWN — log không có câu trả lời; chờ Nguyên bổ sung nếu đã hỏi.

## Tổng hợp

- Chủ đề lặp nhiều nhất: BS viết theo cách bảng tra chưa phủ — "Huongdan" không "/", biệt dược "vigentin", "amlodipin", "cao huyết áp" (người 2; người 1 dùng kịch bản mẫu nên không thử điểm này). Trùng phát hiện nhóm tự thử 28/11 ("tăng huyết áp", "đặt stent"). Chỉ 2 người, 4 lượt: chưa đủ để gọi là xu hướng.
- Sửa gì trước demo (ghi `spec.md` §10): "chi tiết" lặp lại cả tin — đã sửa (PR #43, deploy 12:29). alias vigentin, amlodipin(e), amlor, norvasc + `DDI-037`/`DDI-038` (NSAID / macrolide × amlodipine): đã thêm, chưa deploy. "Huongdan" không "/": đang sửa ở branch `fix/huongdan-tha-on-dinh`. Chưa ghi `spec.md` §10.
- Giữ gì và vì sao: gặp thuốc lạ, bot nói "chưa có dữ liệu… nên không đoán" và không ra ✅ (người 2) — tránh trấn an sai.
- Để dành sau: BS RHM đọc lại câu chữ `DDI-037`/`DDI-038`; "cao huyết áp" / "tăng huyết áp" không kèm tình trạng, "đặt stent"; hỏi 2 người thử câu "nếu mai không được dùng nữa".
