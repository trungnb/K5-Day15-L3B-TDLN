# Reflection — Nguyễn Lương Nguyên

> Thành viên nhóm `TDLN` (Lớp `L3B` · Track `B` — Y tế) · Mã học viên `2A202604005`.

1. **Vai trò + phần mình làm (trỏ tới file / commit):**
   - Phụ trách BA và tích hợp ([TEAMS.md](../TEAMS.md) dòng 3): viết [spec.md](../spec.md) §2, dùng cận dưới có nguồn cho số BS RHM (PR `#1`), và §3 về giải pháp tương tự (PR `#4`). Điền [README.md](../README.md) và [docs/ai-usage.md](../docs/ai-usage.md) (PR `#9`). Viết §10 gồm bảng phân công, khai báo dùng AI và changelog sau CP2 (PR `#25`, `#28`).
   - Mảng dữ liệu: gom 48 câu hỏi đáp RHM công khai trên AloBacsi, kèm `evidence/crawl_qa.py` và `evidence/count_qa.py` để Đức kiểm đếm (PR `#2`). Tách thuốc phối hợp thành nhiều dòng alias và thêm luật `combo:` vào `data/build/validate_csv.py` (PR `#5`).
   - Mảng bot Zalo: bot báo BS khi ca chờ bổ sung quá 10 phút, thay vì lặng lẽ bỏ ca (PR `#26`). Viết kịch bản trực bot 5 nhịp [validation/kich-ban-truc-bot.md](../validation/kich-ban-truc-bot.md) (PR `#38`). Tái cấu trúc bản tin thành dữ liệu có cấu trúc `Reply` trong [codebase/reply.py](../codebase/reply.py), gom trạng thái chat vào `Conversation` ở bot và tách bảng `data/rule_behavior.csv`, `data/build/alias_specs.csv` (PR `#49`, `08f9534`). Thay đổi này không đổi output: 62 ca phát lại khớp từng ký tự.
   - Review PR `#21`, `#30`, `#33` của bạn trong nhóm. Mở issue `#32` (bot thỉnh thoảng bỏ sót tin) và `#31` (câu trả lời còn khô).

2. **AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):**
   - Dùng Claude Code (Claude Opus 5.5) cho gần hết phần việc: tìm và tóm tắt nguồn cho `spec.md` §2–§3, viết script crawl/đếm, `expand_combo_rows()`, sửa bot, review PR và tái cấu trúc ở PR `#49`.
   - Mình phải tự kiểm lại output của AI ở các chỗ sau:
     - Nhãn nháp AI gán cho `qa_sample.csv`: mình kiểm tay 15 dòng, khớp 15/15.
     - Trang gốc của nguồn §3: công cụ không mở được, phải mở lại bằng trình duyệt.
     - Changelog §10 do AI soạn: Trung review chỉ ra 7 điểm, mình sửa hết (PR `#25`).
     - PR `#26` lúc đầu sót nhánh agent lỗi, khi đó ca quá hạn vẫn bị bỏ lặng lẽ. Phải sửa thêm trong `59692c9`.
   - Với PR `#49`, mình không tin câu "không đổi hành vi" của AI. Mình bắt nó chứng minh bằng cách phát lại câu trả lời model đã ghi trong `traces/run-1`, `run-2` cho 62 ca, rồi so 5 dạng output từng ký tự.
   - Có một lần AI báo builder "khớp hoàn toàn", nhưng máy không có `data/raw/ddinter` nên phép so đó vô nghĩa. Mình phải đổi sang so trực tiếp `build_alias_rows` cũ và mới.
   - Việc chưa chắc thì mình chỉ mở issue, chưa cho AI sửa: làm câu trả lời bớt khô (`#31`) đụng câu chữ Trung đã duyệt và sát CP4.

3. **Một câu thử trượt của nhóm và mình học được gì từ nó:**
   - Chọn **`B13`**: *"viêm mô tế bào má phải… cho giảm đau (para) + kháng sinh (azithro...), 2 thuốc trên có tương tác gì bất lợi không?"*. Câu này trượt ở cả hai lượt (xem [eval/report.md](../eval/report.md)).
   - Ở lượt 1, bot nhận ra paracetamol và azithromycin. Bảng `ddi_rules.csv` không có quy tắc cho cặp này, nên bot không cảnh báo gì và cũng không nói là bảng không có quy tắc. BS đọc tin dễ hiểu nhầm thành "đã kiểm, không có tương tác".
   - Ở lượt 2, bot đã có dòng ℹ️ "Bảng tra hiện chưa có quy tắc tương tác cho cặp…", nhưng vẫn trượt vì chưa hướng BS đánh giá sớm khi ca được mô tả là cấp.
   - Bài học cho phần dữ liệu mình phụ trách: bảng không có quy tắc không có nghĩa là an toàn. Độ phủ của bảng phải được nói ra trong câu trả lời, không được im lặng.
   - Câu `B14` cùng lớp lỗi, chỉ khác ở phía bí danh: BS viết "ibu" nhưng bảng chưa có alias này. Khi trực bot, BS ngoài nhóm cũng viết "vigentin", "amlodipin" theo những cách bảng chưa phủ ([validation/log.md](../validation/log.md)). Alias nên được gom từ cách BS nhắn thật, không chỉ từ tên trong danh mục thuốc.
