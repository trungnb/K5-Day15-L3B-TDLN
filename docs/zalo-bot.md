# Hướng dẫn tạo & chạy Zalo Bot (bản mới sạch cho Hackathon)

## 0. Nguyên tắc

- `bot/zalo_bot.py` chỉ là **lớp vỏ mỏng** nhận tin từ Zalo → gọi `answer(text)` trong `codebase/agent.py` → trả lời lại. Toàn bộ logic y khoa và tra cứu nằm trong `codebase/`.
- Token bot để trong file `.env` ở **thư mục gốc repo** (cùng chỗ với `MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY`), tuyệt đối không commit.
- Bot dùng lại cấu trúc SDK `python-zalo-bot` và cách cắt tin nhắn từ bài lab cũ `LAB/zalobot` của chính nhóm — nhớ ghi rõ trong `docs/ai-usage.md`.

---

## 1. Tạo bot mới trên Zalo (khoảng 5 phút)

1. Mở ứng dụng **Zalo** trên điện thoại.
2. Tìm Official Account có tên **Zalo Bot Manager**.
3. Nhấn **Tạo bot** trong khung chat để mở giao diện **Zalo Bot Creator**.
4. Đặt tên bot bắt đầu bằng tiền tố **`Bot`** (ví dụ: `Bot RHM An Toàn`), điền các thông tin được hỏi rồi bấm tạo.
5. Hệ thống Zalo sẽ gửi **Bot Token** trực tiếp qua tin nhắn Zalo.

> **Lưu ý kiểm lại:** Các bước bấm nút trên ghi theo tài liệu Zalo Bot Platform — kiểm lại đúng tên nút trên màn hình lúc thao tác.
> **Bảo mật:** Không dán Bot Token vào nhóm chat, slide, video hay ảnh chụp màn hình. Nếu lỡ lộ token, thu hồi/tạo lại token hoặc tạo bot mới ngay *(vị trí chính xác của nút reset token trên Zalo Bot Creator: `UNVERIFIED`)*.

---

## 2. Cài đặt môi trường cho bot

`run.py`, `eval` và `simulate` chỉ dùng thư viện chuẩn Python và **không cần** cài môi trường này. Riêng máy chạy bot Zalo thì chạy từ **thư mục gốc repo**:

```bash
python3 -m venv bot/.venv && bot/.venv/bin/pip install -r requirements.txt
```

---

## 3. Cấu hình `.env` ở thư mục gốc repo

Nếu chưa có `.env`, chép từ mẫu: `cp .env.example .env`. Sau đó điền thêm 2 dòng cho Zalo Bot:

```env
ZALO_BOT_TOKEN=<dán_token_của_bạn>
ZALO_ALLOWED_CHAT_IDS=
```

*(Để trống `ZALO_ALLOWED_CHAT_IDS` ở lần chạy đầu để lấy `chat_id` của chính bạn.)*

---

## 4. Chạy thử & lấy `chat_id` của chính mình

1. Khởi động bot từ thư mục gốc repo:
   ```bash
   bot/.venv/bin/python bot/zalo_bot.py
   ```
2. Mở Zalo, tìm đúng bot vừa tạo và nhắn `/start`.
3. Bot sẽ trả về: `Chat id của bạn là <id>. Gửi id này cho nhóm để được cấp quyền dùng thử.`
4. Dán `<id>` vào `ZALO_ALLOWED_CHAT_IDS` trong `.env` (nhiều id cách nhau bằng dấu phẩy `,`).
5. Nhấn `Ctrl+C` tắt bot và chạy lại `bot/.venv/bin/python bot/zalo_bot.py`, nhắn `/start` lần nữa để thấy hướng dẫn đầy đủ.

---

## 5. Thêm bác sĩ RHM vào danh sách dùng thử

1. Gửi link/tên bot cho BS thử nghiệm và nhờ BS nhắn `/start`.
2. BS chụp/nhắn lại `chat_id` bot vừa trả về.
3. Nhóm thêm `chat_id` đó vào `ZALO_ALLOWED_CHAT_IDS` trong `.env` rồi khởi động lại bot.
4. Nhắc BS **chỉ nhập ca giả lập hoặc đã ẩn danh** — không gửi tên, SĐT, mã hồ sơ hay ảnh đơn thuốc thật.

---

## 6. Checklist trước khi demo live

- [ ] `.env` đang để `MODEL_PROVIDER` và `MODEL_NAME` thật (không phải `fake`).
- [ ] Chạy bot kèm `caffeinate -i` trên macOS để máy không ngủ giữa buổi demo:
  ```bash
  caffeinate -i bot/.venv/bin/python bot/zalo_bot.py
  ```
- [ ] Kiểm tra kết nối mạng ổn định trước khi vào zone demo.
- [ ] Chuẩn bị sẵn phương án dự phòng: chạy CLI `python3 run.py` và mở sẵn link video dự phòng.

---

## 7. Log hội thoại

- Mỗi lượt chat được ghi vào `bot/logs/YYYYMMDD.jsonl` (đã thêm vào `.gitignore` — không đẩy lên GitHub).
- Trong log chỉ lưu hash 10 ký tự đầu của `chat_id`, không lưu token.
- Khi tổng hợp vào `validation/log.md` cho phần Bonus, **chỉ chép đoạn đã viết lại và bỏ tên**, không gắn thông tin nhận diện người thử.
- Sau khi hoàn tất tổng hợp dữ liệu thử nghiệm, xoá thư mục `bot/logs/`.

---

## 8. Lỗi hay gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Nhắn cho bot không thấy phản hồi | Kiểm tra cửa sổ terminal bot còn chạy không và `ZALO_BOT_TOKEN` trong `.env` có đúng không (không thừa dấu cách/ngoặc kép). |
| `getUpdates` không nhận được tin | Nếu bot từng được cấu hình Webhook trước đó, hãy gọi API xoá webhook theo tài liệu Zalo trước khi dùng polling. |
| Bot báo "chưa được cấp quyền" | Kiểm tra `chat_id` đã có trong `ZALO_ALLOWED_CHAT_IDS` chưa, và nhớ khởi động lại bot sau khi sửa `.env`. |
| Bot trả lời chậm | Thường do độ trễ phản hồi của model AI; kiểm tra log terminal hoặc chạy thử 1 câu bằng `python3 run.py`. |
| Tin nhắn dài bị chia thành nhiều tin | Hành vi bình thường: bot tự tách mỗi tin ≤ 1900 ký tự để không vượt ngưỡng của Zalo. |

---

## 9. Những việc bot KHÔNG làm

- Không nhận lệnh `/send` hay giữ danh bạ SĐT bệnh nhân như bản lab cũ.
- Không lưu hồ sơ bệnh nhân, không nhận ảnh đơn thuốc.
- Không kê đơn thay thế, không tư vấn liều, không khuyên tự ngưng thuốc nền.

---

## Mục `UNVERIFIED` (cần kiểm thực tế lúc tạo bot)

- Tài khoản Zalo của người ngoài (không phải chủ tạo bot) có nhắn tin được vào bot ở trạng thái mới tạo hay cần bật chế độ/duyệt riêng: **UNVERIFIED** (cần kiểm bằng tài khoản Zalo thứ hai).
- Giới hạn tần suất (rate limit) của API `getUpdates` / `sendMessage` trên Zalo Bot Creator: **UNVERIFIED**.
- Giới hạn `2000` ký tự mỗi lần gửi `sendMessage`: lấy theo hằng số `MAX_MESSAGE_LEN = 2000` trong code `LAB/zalobot/bot.py` của bài lab trước, chưa kiểm lại trực tiếp trên tài liệu API bản mới nhất.
