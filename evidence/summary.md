# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ · `N = 48` câu AloBacsi, Đức kiểm tay `48/48`, có script đếm lại và 6 ví dụ bỏ định danh | [data-mining.md](data-mining.md) |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☑ · có 5 BS ngoài nhóm và 9 trích dẫn đã bỏ định danh | [P1](interviews/P1.md), [P2](interviews/P2.md), [P3](interviews/P3.md), [P4](interviews/P4.md), [P5](interviews/P5.md) |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ | `evidence/survey/` |

## 2. Số chính

- Đào data: mẫu `N = 48` URL AloBacsi (2 chuyên mục Nha khoa & Răng Hàm Mặt, xem 27/11/2026; kiểm bằng `python3 evidence/count_qa.py`): **`1/48 (2%)`** câu nhắc bệnh nền gắn với làm răng (`Q32` — đặt stent 3 tháng muốn làm răng giả; `thuoc_nen = 0/48`, `di_ung = 0/48`), và **`1/48 (2%)`** câu đang cho con bú hỏi nhổ răng và thuốc giảm đau (`Q39`, thống kê riêng).
- Phỏng vấn: 5 phản hồi từ 5 BS ngoài nhóm theo xác nhận của Trung. P1 kể một ca xử lý theo kinh nghiệm và không tra cứu. P2 và P3 mỗi người kể một ca phải hỏi BS nội khoa, tự báo cáo lần lượt 2 lần và khoảng 5 lần rà soát trong tháng. Hai ca được kể mất khoảng 90 phút (P2) và 3 phút (P3) để xử lý. P4 báo 1 lần trong tháng, có tra web và phòng khám trao đổi với dược sĩ tại chỗ. P5 báo 1 lần trong tháng (cách đây 1 tuần), ca tăng huyết áp đang điều trị phải tạm hoãn nhổ răng và hướng dẫn vào viện khám/điều trị huyết áp trước; nêu bất tiện “bệnh nhân không nhớ tên thuốc”. Thời gian riêng để tra cứu vẫn `UNKNOWN`.
- Khảo sát: n = __ · __/__ (__%) …

Phỏng vấn nhiều vai thì đếm theo từng vai, không cộng chung.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | BS phẫu thuật RHM · 6 năm kinh nghiệm | Có tình huống cần cân nhắc · ca kể không tra cứu | Trả lời “1 ca” · chưa rõ có phải dừng để tra hoặc hội chẩn | `UNKNOWN` | Dựa vào kinh nghiệm |
| P2 | BS chuyên RTE · 6 năm kinh nghiệm | Có ca cụ thể phải hỏi chuyên khoa · khó liên hệ BS và tra chéo | 2 lần tự báo cáo · kể cụ thể 1 lần | 90 phút xử lý tình huống (tự báo cáo) | Hỏi BS nội khoa rồi hướng đi khám chuyên khoa |
| P3 | BS RHM · 1 năm kinh nghiệm | Có ca cụ thể phải hỏi BS nội khoa · vướng tra tương tác chéo | Khoảng 5 lần tự báo cáo · kể cụ thể 1 lần | Khoảng 3 phút xử lý tình huống (tự báo cáo) | Hỏi bệnh nhân và hỏi BS nội khoa |
| P4 | BS nha khoa tổng quát · 6 năm kinh nghiệm | Có tình huống cần rà soát · trả lời “Không” khi hỏi về bất tiện | 1 lần tự báo cáo | `UNKNOWN` | Tra web · phòng khám trao đổi với dược sĩ tại chỗ |
| P5 | BS chỉnh nha · 6 năm kinh nghiệm | Có ca bệnh nền phải tạm hoãn nhổ răng · bất tiện ở khâu BN không nhớ tên thuốc | 1 lần tự báo cáo (cách đây 1 tuần) | `UNKNOWN` | Hướng dẫn BN vào viện khám và điều trị huyết áp trước khi nhổ răng |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

1. “Mình đã có kn về dị ứng kháng sinh loại này nên mình k tra.” — [P1](interviews/P1.md)
2. “Rhm xài thuốc cơ bản nên có thể làm bảng ghi rõ sẵn các thuốc dự phòng nếu có dị ứng,…” — [P1](interviews/P1.md)
3. “Hỏi bs nội khoa sau đó Cho đi khám thêm chuyên khoa nội, 1.5 tiếng” — [P2](interviews/P2.md)
4. “Bất tiện: không phải lúc nào cũng gọi điện gặp được bs, khó khăn trong tra chéo tương tác thuốc” — [P2](interviews/P2.md)
5. “Hỏi bệnh nhân + Hỏi nội khoa. Tốn khoảng 3 phút” — [P3](interviews/P3.md)
6. “Tra tương tác chéo vường hơn” — [P3](interviews/P3.md)
7. “Tra cứu web + phòng khám có ý kiến với dược sĩ tại phòng khám” — [P4](interviews/P4.md), phản hồi bổ sung
8. “Hướng dẫn bệnh nhân vào viện khám và điều trị huyết áp trước khi nhổ răng” — [P5](interviews/P5.md)
9. “Bất tiện: bệnh nhân không nhớ tên thuốc” — [P5](interviews/P5.md)

## 4. Các nguồn có khớp nhau không

Data AloBacsi (`N = 48`) có **`1/48 (2%)`** câu nhắc bệnh nền (`Q32`: đặt stent 3 tháng muốn làm răng giả) và **`1/48 (2%)`** đang cho con bú (`Q39`); ngay cả ở `Q32` hay `Q33` người bệnh cũng không tự khai tên thuốc đang dùng (`thuoc_nen = 0/48`). Trong khi đó phỏng vấn BS (`P1–P5`) ghi nhận hai vướng mắc thực tế tại ghế răng: tra chéo tương tác / gọi BS nội khoa (`P2`, `P3`) và bệnh nhân không nhớ tên thuốc buộc phải tạm hoãn nhổ răng (`P5`). Hai nguồn **khớp nhau ở chỗ người bệnh thường không nêu rõ tên thuốc đang dùng**, nhưng **lệch về cơ cấu mẫu**: hỏi đáp công khai trên mạng thiên về niềng răng/bọc sứ/răng khôn hơn là sàng lọc bệnh nền nội khoa tại phòng khám.

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md` **đạt một phần (theo hướng kiểm chứng định tính + đối chứng)**: vế phỏng vấn ghi nhận BS phải dừng lại hỏi nội khoa / tra chéo (`P2`, `P3`) hoặc tạm hoãn nhổ răng vì BN không nhớ tên thuốc (`P5`, khớp giả thuyết đối chứng trong `evidence/hypothesis.md`), trong khi `P1` tự xử lý theo kinh nghiệm và `P4` tra web cùng dược sĩ tại chỗ. Ngược lại, **vế đào data không đạt ngưỡng `≥ 20%`** (chỉ đạt **`1/48 = 2%`** bệnh nền và **`1/48 = 2%`** cho con bú) do mẫu hỏi đáp phổ thông trên AloBacsi phần lớn là thắc mắc niềng răng/thẩm mỹ. Như đã ghi ở trên, tỷ lệ `2%` và 5 ca phỏng vấn mô tả ca riêng lẻ, chưa đủ căn cứ để ngoại suy impact toàn quốc.

## Lịch hẹn (dùng cho CP2 — chỉ ghi vai và giờ, không tên)

| Vai | Giờ hẹn | Đã xong? |
|---|---|---|
| | | |
