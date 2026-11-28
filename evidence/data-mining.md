# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Script / công thức đếm để trong repo (`evidence/count_qa.py`), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — bỏ tên người hỏi, bỏ chi tiết định danh bệnh nhân, trích tối đa 2 câu mỗi mục, ghi link và ngày xem.

## 1. Cách đếm — viết TRƯỚC khi chạy

- **Nguồn:** Trang đầu của hai mục AloBacsi [Nha khoa](https://alobacsi.com/kham-benh-online/nha-khoa) và [Răng Hàm Mặt](https://alobacsi.com/kham-benh-online/rang-ham-mat), xem ngày 27/11/2026.
- **Lấy mẫu:** Lấy các bài hiển thị trên trang đầu của từng mục, gộp theo URL và bỏ trùng. Script chỉ giữ bài đọc được dữ liệu câu hỏi và ngày đăng. Bộ cố định có 48 URL duy nhất, đăng từ 27/05/2025 đến 26/11/2026. Đây là mẫu theo hai trang danh mục; không suy rộng thành các bài mới nhất trên toàn trang.
- **Mẫu số:** N = 48 gồm cả dòng âm tính. CSV giữ mã, URL, ngày và nhãn nháp để Đức rà; mở link gốc khi cần kiểm. Chỉ đưa các trích dẫn đã chọn và bỏ định danh vào phần ví dụ.
- **Tử số chính:** Câu có bệnh nền, thuốc nền hoặc dị ứng gắn với thủ thuật hoặc thuốc RHM. Mang thai/cho bú báo riêng. Mỗi nhãn chỉ đếm một lần trên một câu.
- **Chạy lại:** python3 evidence/count_qa.py. Đức rà toàn bộ nhãn trước khi điền kết quả và ghi số kiểm tay vào docs/ai-usage.md.

## 2. Đọc trước, đếm sau

Đã đọc và kiểm tay toàn bộ **48/48** câu hỏi gốc từ các đường dẫn trong `evidence/qa_sample.csv` (khớp **48/48** nhãn nháp ban đầu). Các kiểu câu hỏi thấy được trước khi chốt số:
- **Chỉnh nha & thẩm mỹ (niềng răng, bọc sứ, dán veneer):** chiếm phần lớn (gồm nhóm `Q03–Q09`, `Q14–Q15`, `Q17`, `Q21`), hỏi về nhổ răng tạo khoảng, mài kẽ, độ tuổi làm răng.
- **Răng khôn, sâu răng, điều trị tủy & răng trẻ em:** hỏi đau ê ẩm sau lấy tủy/nhổ răng, sưng nướu trùm, sâu răng sữa ở trẻ nhỏ.
- **Triệu chứng niêm mạc / răng miệng chưa rõ nguyên nhân:** nổi nhú thịt, nướu chuyển màu trắng, hôi miệng, chảy máu kẽ răng hoặc chân răng sứ.
- **Nhóm có yếu tố toàn thân gắn với làm răng / thuốc RHM:** rất ít câu người bệnh tự nêu thẳng bệnh nền hoặc tình trạng đặc biệt (`Q32` đặt stent mạch vành muốn làm răng giả; `Q39` đang cho con bú hỏi nhổ răng và thuốc giảm đau); ngay cả ca đặt stent `Q32` hay ca đau nướu trùm `Q33` bệnh nhân cũng không ghi tên thuốc đang uống.

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Câu hỏi nhắc bệnh nền / thuốc nền / dị ứng gắn với thủ thuật hoặc thuốc RHM | `1/48` | `2%` | Chỉ có `Q32` (đặt stent mạch vành 3 tháng muốn làm răng giả); `lien_quan=co` |
| — yếu tố `benh_nen` | `1/48` | `2%` | `Q32` (`thu_thuat_thuoc=khac`) |
| — yếu tố `thuoc_nen` | `0/48` | `0%` | Người bệnh không tự ghi tên thuốc đang dùng |
| — yếu tố `di_ung` | `0/48` | `0%` | — |
| Mang thai / cho bú gắn với thủ thuật hoặc thuốc RHM *(thống kê riêng)* | `1/48` | `2%` | `Q39` (đang cho con bú hỏi nhổ răng và thuốc giảm đau: `nho_rang\|giam_dau`) |

Chạy lại kiểm chứng: `python3 evidence/count_qa.py` cho ra đúng bảng số trên (đã bỏ nhãn `AI-nhap`, ghi `Nguyen, Duc`).

## 4. ≥5 ví dụ cụ thể (mã dòng / link + ngày xem, bỏ tên)

1. **`Q32` (Dương tính — bệnh nền):** *"cho e hỏi xíu ạ e năm nay e 42 tuổi đặt 1sten được 3 tháng giờ e muốn làm bộ răng được ko ạ"* — [AloBacsi](https://alobacsi.com/kham-benh-online/dat-stent-3-thang-di-lam-rang-gia-co-an-toan-khong.html), xem `27/11/2026` *(nhãn: `lien_quan=co`, `benh_nen`, `khac`)*.
2. **`Q39` (Dương tính — nhóm mang thai/cho bú báo riêng):** *"Tôi bị sâu răng cùng, răng lại mọc lệch, đau nhức quá nên muốn nhổ, nhưng tôi đang cho con bú thì có nhổ răng được không? Có thể uống thuốc gì giảm đau ạ?"* — [AloBacsi](https://alobacsi.com/kham-benh-online/dang-cho-con-bu-co-nho-rang-duoc-khong.html), xem `27/11/2026` *(nhãn: `lien_quan=co`, `mang_thai_cho_bu`, `nho_rang|giam_dau`)*.
3. **`Q30` (Giáp ranh — loại khỏi tử số):** *"Tôi lỡ uống 1 hộp sữa không đường nhỏ trước khi khám tiền mê thì có làm sai kết quả? Cách đây 3 tháng đã xét nghiệm đường huyết bình thường."* — [AloBacsi](https://alobacsi.com/kham-benh-online/xet-nghiem-tien-me-de-nho-rang-khon-lo-uong-sua-co-lam-sai-ket-qua.html), xem `27/11/2026` *(loại vì hỏi về ăn uống trước xét nghiệm tiền mê, không khai mắc bệnh nền hay đang uống thuốc nền)*.
4. **`Q25` (Giáp ranh — loại khỏi tử số):** *"Thưa bác sĩ, nếu cần nhổ răng khôn hàm trên hoặc hàm dưới thì nên thực hiện tại bệnh viện lớn hay có thể nhổ tại phòng khám nha khoa? Những trường hợp nào cần đến bệnh viện để đảm bảo an toàn?"* — [AloBacsi](https://alobacsi.com/kham-benh-online/nho-rang-khon-nen-thuc-hien-o-benh-vien-hay-phong-nha.html), xem `27/11/2026` *(loại vì hỏi tiêu chí chung, không nêu bệnh nền/thuốc nền của cá nhân)*.
5. **`Q33` (Giáp ranh — loại khỏi tử số):** *"Gần đây nướu răng tôi đau và tai cũng đau ngắt quãng. Tôi ra nhà thuốc mua thuốc uống, nhưng hết thuốc bị đau lại."* — [AloBacsi](https://alobacsi.com/kham-benh-online/nuou-trum-rang-khon-gay-dau-lan-len-tai-phai-lam-sao.html), xem `27/11/2026` *(loại vì chỉ nhắc mua thuốc giảm đau triệu chứng răng khôn, không nêu thuốc nền/bệnh nền/dị ứng)*.
6. **`Q03` (Âm tính — câu nha khoa phổ thông):** *"Vì sao khi nhắc đến niềng răng, nhiều người thường nghĩ ngay đến việc phải nhổ hai hoặc bốn chiếc răng, thậm chí là những chiếc răng hoàn toàn khỏe mạnh? Tại sao có người cần nhổ răng khi niềng, trong khi những người khác lại không cần?"* — [AloBacsi](https://alobacsi.com/kham-benh-online/vi-sao-khi-nieng-rang-lai-phai-nho-rang.html), xem `27/11/2026` *(nhãn: `khong`)*.

## 5. Giới hạn của data

- Câu hỏi trên mạng là góc nhìn **bệnh nhân tự hỏi** (thường lo lắng trước khi đi làm răng hoặc sau khi đọc đơn), **không phải** log tra cứu nội bộ của bác sĩ RHM.
- Vì vậy nguồn này chỉ dùng làm **nguồn thứ 2 kiểm chéo** với nguồn chính là phỏng vấn ≥3 BS RHM ngoài nhóm: kiểm xem các nhóm bệnh nền/thuốc nền nào gây lo ngại và xuất hiện lặp lại ở cả 2 phía (bệnh nhân hỏi ↔ bác sĩ phải xử lý).
- **Lệch và thiếu sau khi chạy (`1/48 = 2%` cho tử số chính, `1/48 = 2%` mang thai/cho bú):** Mẫu hai trang đầu AloBacsi thiên về câu hỏi thẩm mỹ/niềng răng phổ thông nên tỷ lệ nhắc bệnh nền (`2%`) thấp hơn hẳn mức `≥ 20%` dự đoán ban đầu trong `evidence/hypothesis.md`. Tuy vậy, mẫu này lại bộc lộ rõ một đặc điểm thực tế: ngay cả người bệnh có bệnh tim mạch nặng như đặt stent (`Q32`) cũng **không tự khai tên thuốc chống đông/kháng tiểu cầu** khi đặt câu hỏi, khớp với bất tiện *"bệnh nhân không nhớ tên thuốc"* mà BS phỏng vấn `P5` nêu ra.
→ Kiểm lại bằng phỏng vấn: `evidence/interviews/P1.md`… (`evidence/summary.md`).
