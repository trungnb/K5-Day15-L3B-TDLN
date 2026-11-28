# Kịch bản trực bot — BS ngoài nhóm dùng thử Bot Zalo

> Dùng cho phiên **11:30–13:00 Thứ Bảy 28/11** (`docs/team-plan.md` §D). Kết quả ghi vào [`log.md`](log.md).
> Theo 5 nhịp của guide bước 4.3: **làm quen · bối cảnh · giao việc · quan sát · hỏi sau**. 2–3 BS RHM ngoài nhóm, ~10 phút / người.
> Mục tiêu: **thấy chỗ BS do dự, hiểu sai hoặc bỏ cuộc**, không phải để bot được khen. Toàn lời khen = phiên chưa đạt → giao việc khó hơn (V3).

## 0. Chuẩn bị (11:15–11:30)

- [ ] **VM chạy bản mới nhất** của `bot/` (có #30, #33, #35). Nhắn `/start` từ tài khoản test, bot trả lời trong ~10 giây.
- [ ] `ps aux | grep zalo_bot` trên VM: **chỉ 1 tiến trình** (issue #32, nguyên nhân C).
- [ ] Mã mời sẵn sàng. Gửi riêng cho từng BS, không đăng lên nhóm chung.
- [ ] 3 thẻ việc (mục 3) in ra hoặc để sẵn để dán vào chat.
- [ ] Đồng hồ bấm giờ và mẫu ghi nhanh (mục 7) cho từng người.
- [ ] **Phân vai:**
  - **Trung** dẫn phiên: là BS, nói chuyện với BS dễ hơn.
  - **Nguyên** ghi chép, **không nói**, không chỉ màn hình.
- [ ] Cách quan sát: ngồi cạnh, hoặc gọi video có chia sẻ màn hình điện thoại. Không quan sát được màn hình thì chỉ ghi được lời nói, và phải ghi rõ hạn chế đó vào `log.md`.

**An toàn:**
- Chỉ dùng ca **giả lập hoặc đã ẩn danh**. Không họ tên, SĐT, mã hồ sơ hay ảnh đơn thuốc thật.
- Nhắc BS rằng hôm nay **không dùng kết quả của bot cho BN thật**.

## 1. Làm quen (~1 phút)

> "Cảm ơn anh/chị dành 10 phút. Bọn em đang thử **cái bot**, không phải thử anh/chị, nên không có thao tác nào là sai. Anh/chị cứ vừa làm vừa nói to những gì đang nghĩ, kể cả 'chỗ này khó hiểu'. Em ghi chép nhưng không ghi tên. Hôm nay chỉ dùng ca giả, đừng nhập thông tin BN thật."

Kích hoạt bot bằng mã mời. **Không giải thích tính năng**: không nói trước về `/moi`, "thêm …", "chi tiết", `/sai`. Mục đích là xem BS có tự tìm ra hay không.

## 2. Bối cảnh (~2 phút)

Hỏi về **lần gần nhất có thật**, không hỏi ý kiến chung chung:

> "Lần gần nhất anh/chị phải dừng lại để xem bệnh nền hay thuốc BN đang uống trước khi nhổ răng hoặc kê đơn là khi nào? Lúc đó anh/chị làm gì?"

Ghi nguyên văn **cách họ đang xoay xở**: tra web, gọi BS nội khoa, hỏi dược sĩ hay theo kinh nghiệm. Đừng gợi ý câu trả lời và đừng nhắc tới bot.

## 3. Giao việc (~5 phút)

Đưa **kết quả cần đạt**, không đưa các bước. Không đọc giúp, không gõ giúp.

| Thẻ | Đưa cho BS | Thử điều gì | Nhóm mong thấy |
|---|---|---|---|
| **V1 · thường** | "BN nam 60 tuổi, đang uống thuốc chống đông. Chiều nay anh/chị định nhổ răng khôn rồi kê thuốc giảm đau. Dùng bot để biết trước có gì cần lưu ý." | BS tự gõ tên thuốc theo thói quen (Sintrom, warfarin, viết tắt…) | Gõ warfarin / Sintrom (nhóm kháng vitamin K): **CR-001** (× nhổ răng) và, nếu kê NSAID, **DDI-001** HIGH. Gõ chung "thuốc chống đông" không tên: bot phải **hỏi tên thuốc** (❔), **không** được ra ✅. Gõ thuốc chống đông mới (DOAC, vd Xarelto): ghi lại bot trả gì, rule khác CR-001 |
| **V2 · khó** | "BN đang dùng **Coplavix**. Anh/chị chưa quyết kê giảm đau gì. Hỏi bot rồi chọn." | Thuốc phối hợp; BS có nhắn bổ sung thành tin thứ hai không; bot có ghép tin không | Ghép tin bổ sung; nếu kê ibuprofen: **DDI-004** HIGH (aspirin × ibuprofen) |
| **V3 · khó hơn** (dùng khi V1, V2 trôi chảy hoặc toàn lời khen) | "Giờ chuyển sang một BN khác: đang mang thai 7 tháng, định kê giảm đau cho đau răng. Hỏi bot luôn liều bao nhiêu." | BS có biết chuyển ca (`/moi`) không; phản ứng với câu từ chối liều 🚫 | Ca mới **không** dính thuốc của BN trước; cảnh báo **CR-013** nếu là NSAID; từ chối tư vấn liều |

Kẹt hơn **60 giây**: gợi ý tối thiểu ("Anh/chị định nhắn gì tiếp?"), rồi ghi **"được gợi ý"** vào quan sát.

## 4. Quan sát (trong lúc giao việc)

Nguyên ghi **hành vi**, mỗi dòng kèm giờ. Giờ là bắt buộc để đối chiếu `bot/logs` nếu bot miss tin, xem issue #32.

- Gõ **gì đầu tiên** (chép nguyên văn), và mất bao lâu tới tin đầu.
- **Chỗ dừng > 5 giây**: đang nhìn phần nào của câu trả lời?
- **Đọc phần nào trước**: 🔴 hay "📋 Em đã đối chiếu"? Có cuộn xuống đọc nguồn không?
- Có hiểu **mã** `[DDI-…]` / `[CR-…]` không? Có hỏi lại "mã này là gì" không?
- Phản ứng với ✅ "Không phát hiện cảnh báo…": BS có hiểu thành **"an toàn"** không?
- Có tự tìm ra `/moi`, "thêm …", "chi tiết" không?
- **Bot không trả lời** tin nào: ghi giờ và nội dung tin (đã ẩn danh).
- Bot **sai hoặc sót** cảnh báo so với cột "Nhóm mong thấy": ghi ngay, đánh **mức cao**.

## 5. Hỏi sau (~2 phút)

Hỏi về việc đã xảy ra, không hỏi "anh/chị thấy bot hay không":

1. "Lúc nào anh/chị thấy khó hiểu hoặc phải đoán nhất?"
2. "Có câu nào bot nói mà anh/chị **không tin** hoặc sẽ kiểm lại?"
3. "Tuần sau nếu có bot này, anh/chị dùng cho ca nào, và **không** dùng cho ca nào?"
4. **Bắt buộc**, đọc đúng câu: *"Nếu mai không được dùng nữa, bạn thấy: rất tiếc / hơi tiếc / không sao?"*

## 6. Mức nghiêm trọng (cột cuối của `log.md`)

| Mức | Khi nào |
|---|---|
| **Cao** | Bot sai hoặc sót cảnh báo HIGH; BS hiểu ✅ là "an toàn"; BS không hoàn thành việc; bot không trả lời |
| **Vừa** | Hoàn thành nhưng phải được gợi ý, hoặc do dự rõ (> 30 giây) ở một bước |
| **Thấp** | Khó chịu nhỏ: câu dài, từ khó hiểu, phải cuộn nhiều |

## 7. Mẫu ghi nhanh (một tờ cho mỗi người thử)

```
Người thử #__ · Vai: BS ______ · __ năm KN · Quan sát: ngồi cạnh / video / chỉ lời nói
Bắt đầu: __:__   Kết thúc: __:__

[Bối cảnh] Lần gần nhất: ...
[V1] __:__ gõ đầu tiên: "..."     dừng ở: ...     đúng/sai so với mong đợi: ...
[V2] __:__ gõ đầu tiên: "..."     có nhắn bổ sung? ...   bot ghép? ...
[V3] __:__ ...                    có dùng /moi? ...
Bot không trả lời: __:__ "..."
Trích nguyên văn: "..."
Hỏi sau: (1) ... (2) ... (3) ...   Mai không dùng: rất tiếc / hơi tiếc / không sao
```

## 8. Sau phiên (12:15–13:00)

1. **Trong 15 phút sau mỗi người**, chép từ mẫu ghi nhanh sang bảng [`log.md`](log.md): **chỉ ghi vai, không ghi tên**, trích đã bỏ thông tin định danh (`docs/zalo-bot.md` §7).
2. Điền phần **Tổng hợp** của `log.md`: chủ đề lặp nhiều nhất, sửa gì trước demo, giữ gì, để dành sau.
3. Bot có miss tin: đối chiếu giờ với `bot/logs/*.jsonl` trên VM (giờ **UTC** = giờ VN − 7), tìm `send_error` hoặc `handler_error`, rồi dán kết quả vào issue #32.
4. Sửa gì trước demo thì ghi một dòng vào `spec.md` §10. **Không** sửa `eval/run-*.csv`, câu thử hay chuẩn "đạt".
5. Đưa 1–2 phát hiện chính lên slide trang 8 ("Nếu có thêm 1 tuần") và báo Nguyên trước 13:00.
