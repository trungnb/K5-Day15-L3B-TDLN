# AI SPEC — Trợ lý kiểm tra an toàn trước thủ thuật & kê đơn RHM · Nhóm TDLN · Phòng C401 (T6) · Zone [cập nhật sau Form 1]

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.
> Đầu mỗi mục ghi bước guide (`02-guide.md` trong repo đề) chỉ cách điền. Mỗi mục ngắn, có số và nguồn; chi tiết để ở file được trỏ tới. Xoá dòng hướng dẫn trong ngoặc vuông khi điền xong.

Track: [ ] A · [x] B · [ ] C · [ ] D · [ ] E — bài toán: Mở rộng từ B2 (Kiểm tra tương tác thuốc) sang kiểm tra an toàn bệnh nền + thuốc nền × thủ thuật dự kiến + thuốc định kê cho BS RHM
Data BTC cấp đã dùng (nếu có — không commit nguyên file): Không (Track B tự tổng hợp dữ liệu từ nguồn công khai chính thống)

## §0. Hiện tại việc này diễn ra thế nào *(guide 1.1)*
- Luồng hiện tại của việc này, trên thực hành lâm sàng ngoại trú (4 bước):
  1. Bệnh nhân khai miệng hoặc đưa toa/vỏ thuốc cũ có bệnh nền mạn tính (tim mạch, chống đông, đái tháo đường, tăng huyết áp, bệnh lý xương…) thường ghi bằng tên biệt dược VN hoặc viết tắt.
  2. BS RHM tự nhớ các quy tắc an toàn cơ bản hoặc mở nhiều nguồn rời rạc để tra tay (cổng tra cứu `tuongtacthuoc.nhic.vn`, Dược thư Quốc gia VN, Drugs.com, Medscape).
  3. Với ca phức tạp hoặc không chắc ngưỡng an toàn (vd chỉnh chống đông trước nhổ răng, nguy cơ MRONJ), BS gọi hỏi đồng nghiệp nội khoa/tim mạch hoặc hẹn lại bệnh nhân đi khám chuyên khoa xin giấy xác nhận.
  4. BS ghi nhận rủi ro, làm thủ thuật (hoặc trì hoãn) và tự kê đơn thuốc nha khoa.
- Công cụ / AI đang được dùng cho việc này (nếu có) + nguồn:
  - Các công cụ tra cứu thủ công phổ biến: cổng `https://tuongtacthuoc.nhic.vn/` (Bộ Y tế — chỉ mức chống chỉ định, đòi hỏi nhập đúng tên hoạt chất), Dược thư Quốc gia VN, Drugs.com Drug Interaction Checker, Medscape Drug Interaction Checker.
  - Phần tích hợp cảnh báo tương tác tự động sẵn có trong các phần mềm quản lý phòng khám nha khoa phổ biến tại VN: **chưa kiểm**.

## §1. Người dùng & bằng chứng *(guide 1.1, 1.2)*
- Người dùng chính (một vai cụ thể): Bác sĩ Răng Hàm Mặt (BS RHM) điều trị ngoại trú tại phòng khám / bệnh viện khi khám ca có bệnh nền mạn tính, thuốc nền hoặc dị ứng thuốc.
- Việc họ cố làm xong (`động từ + đối tượng + bối cảnh`, không có chữ AI): Rà soát đầy đủ rủi ro giữa bệnh nền, thuốc nền, dị ứng của bệnh nhân với thủ thuật dự kiến và đơn thuốc nha khoa trước khi thực hiện điều trị tại ghế răng.
- Hôm nay họ giải bằng gì, hỏng ở đâu, vì sao chưa bỏ: Giải bằng trí nhớ cá nhân + tra chéo thủ công trên nhiều web/sách (hoặc hỏi đồng nghiệp); hỏng ở chỗ phải tự quy đổi biệt dược sang hoạt chất, mất thời gian giữa ca khám đông khách, tra tách rời giữa tương tác thuốc–thuốc và chống chỉ định thủ thuật; chưa bỏ vì chưa có công cụ gọn nhẹ nhận tin nhắn tiếng Việt viết tắt và tổng hợp được cả 4 nhánh rủi ro kèm nguồn chính thống. *(Ghi chú bối cảnh: kinh nghiệm thực tế của TV1 Nguyễn Bảo Trung là người trong nhóm chỉ dùng để hiểu luồng việc, không tính là bằng chứng.)*
- Pain (KHÔNG chữ AI): BS RHM khi chuẩn bị làm thủ thuật xâm lấn hoặc kê đơn cho bệnh nhân có bệnh nền và nhiều thuốc nền (thường nêu bằng tên biệt dược VN, viết tắt) phải tra chéo rời rạc nhiều nguồn giữa ca khám áp lực thời gian, dễ mất nhiều phút tra tay hoặc bỏ sót tương tác thuốc–thuốc, thuốc–bệnh nền và rủi ro thủ thuật.
- Bằng chứng — số chính + kết luận (chi tiết: `evidence/summary.md`): Đang thu thập cho CP3 — giả thuyết tại `evidence/hypothesis.md`, nguồn chính là phỏng vấn ≥3 BS RHM ngoài nhóm (`evidence/interviews/P1–P3.md`), nguồn phụ kiểm chéo là đào ≥40 câu hỏi đáp RHM công khai (`evidence/data-mining.md`).

## §2. Impact & quyết định chọn *(guide 1.3)*

| Hướng | Bao nhiêu người gặp | Bao nhiêu lần / tháng | Mỗi lần tốn gì | Impact / tháng | Làm kịp không | Chọn? |
|---|---|---|---|---|---|---|
| **B2-RHM (Mở rộng):** BS RHM kiểm tra an toàn bệnh nền/thuốc nền × thủ thuật & đơn nha khoa | ~4.000 BS RHM (cận dưới, suy ra từ tỉ lệ 1/26.000 dân — xem "Nguồn quy mô BS RHM" dưới bảng) | ~15–25 ca có bệnh nền phức tạp/BS/tháng *(tự ước tính — chờ cập nhật từ P1–P3)* | ~5–10 phút tra tay + rủi ro sót tương tác nặng *(tự ước tính — chờ cập nhật từ P1–P3)* | ~300.000–1.000.000 phút/tháng *(một phần tự ước tính)* | Kịp: danh mục ~20 thuốc RHM & nhóm thủ thuật gọn, dựng được bảng tất định chuẩn nguồn trong 10h; có đầu mối ≥3 BS RHM ngoài nhóm | **Chọn** |
| **B2-BN (Gợi ý gốc):** Người nhà / bệnh nhân mạn tính kiểm tra tương tác & xếp lịch uống thuốc | Hàng triệu người bệnh mạn tính *(tự ước tính)* | ~2–4 lần/tháng khi đổi đơn *(tự ước tính)* | ~10–15 phút đọc hướng dẫn + rủi ro uống nhầm giờ/tương tác *(tự ước tính)* | Rất lớn nhưng phân tán *(tự ước tính)* | Khó: danh mục thuốc toàn bộ chuyên khoa quá rộng, không kịp đối chiếu nguồn từng dòng trong 10h | Loại |
| **B3-Nhà thuốc:** Tư vấn khách hỏi mua thuốc qua chat nhà thuốc tối muộn | Hàng nghìn nhà thuốc *(tự ước tính)* | Hàng trăm lượt chat/nhà thuốc/tháng *(tự ước tính)* | ~3–5 phút dược sĩ trực sàng lọc ca lặp lại *(tự ước tính)* | Lớn *(tự ước tính)* | Khó: khó hẹn ≥3 dược sĩ nhà thuốc phỏng vấn & test trong 2 ngày; rủi ro gợi ý OTC cho trẻ nhỏ/bà bầu cao | Loại |

- **Impact / tháng** của hướng chọn = ~4.000 người × 15–25 lần × 5–10 phút = **~300.000–1.000.000 phút/tháng** (≈ 5.000–16.700 giờ BS/tháng). Số người: cận dưới có nguồn (xem dưới); số lần và số phút: *(tự ước tính — chờ cập nhật từ phỏng vấn P1–P3 trước CP3)*.
- **Nguồn quy mô BS RHM** (chưa có số thống kê chính thức toàn quốc; WHO GHO không có số liệu nha sĩ của Việt Nam; ngày xem 27/11/2026):
  - Tỉ lệ BS RHM/dân tại Việt Nam *"là 1/26.000"* — [Bản tin ĐHQGHN, "Cơ hội và thách thức với ngành RHM"](https://www.vnu.edu.vn/upload/2021/09/29266/file/324%20IN-pages-22-25.pdf) (số liệu khoảng 2016; bài không ghi nguồn gốc tỉ lệ). × ~100 triệu dân *(chưa dẫn nguồn TCTK)* ≈ 3.800 → làm tròn **~4.000, dùng làm cận dưới**.
  - Kiểm chéo: TP.HCM *"có tất cả 2.219 BSRHM"*, tỉ lệ 1/3.998 dân (2023); Tây Nguyên 1/76.086, Đông Nam Bộ 1/51.353 (2017) — [Tạp chí Y học Cộng đồng 65(8), 2024, tr. 54–61](https://tapchiyhcd.vn/index.php/yhcd/article/download/1458/886/1066).
  - Cận trên: Bộ Y tế đặt **mục tiêu** *"Tỷ lệ trung bình Bác sỹ Răng Hàm Mặt so với dân số — 1/10.000 dân"* đến 2030 ([QĐ 5628/QĐ-BYT, Đề án 2021–2030](https://yte.daklak.gov.vn/images_upload/imgND/SYT/files/2_%20Quy%e1%ba%bft%20%c4%91%e1%bb%8bnh%205628-BYT-.pdf)) → hiện tại còn dưới ~10.000.
  - **Đã xem và loại:** "~30.000 licensed dentists" ([Picasso Dental, 2026](https://picassodental.vn/research/dental-clinic-density-vietnam-2026)) — trang của phòng khám tư, tự ghi có lợi ích thương mại; dẫn "Vietnam Dental Association 2025" không có link hay tài liệu gốc. Mâu thuẫn với mục tiêu 1/10.000 dân đến 2030 của QĐ 5628 và mật độ TP.HCM 1/3.998 (2023). Các con số 3.500–12.000 trên trang tuyển sinh/thiết bị nha khoa cũng loại vì không ghi nguồn và năm.
- Hướng ĐÃ LOẠI + vì sao (giữ lại, đừng xoá):
  - **Loại B2-BN:** Phạm vi thuốc nền/thuốc kê đơn toàn bệnh viện quá rộng, dễ rơi vào bẫy "AI tự sinh bảng tương tác" không kịp kiểm chứng từng dòng theo `DATA_CARD.md`.
  - **Loại B3-Nhà thuốc:** Khó tiếp cận đủ ≥3 dược sĩ trực ngoài nhóm trong 2 ngày để lấy bằng chứng phỏng vấn + người dùng thử (bonus), trong khi bài toán gợi ý sản phẩm nhà thuốc có rủi ro pháp lý cao hơn.
- Số lần / tháng của từng kiểu người dùng (dùng cho persona ở §8): Đang chờ tổng hợp từ phỏng vấn P1–P3 (`dung_it` · `dung_vua` · `dung_nhieu`).

## §3. Giải pháp tương tự *(guide 2.1)*
- [sản phẩm / tính năng gần giống]: một điều đáng học · một điều đáng né · mình khác gì

## §4. Thiết kế *(guide 2.2, 3.2)*
- **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả):
- Không làm (≥3 điều):
- **Sơ đồ** (ảnh / Mermaid / draw.io): [chèn ở đây]
- **Hình dạng:** [ ] workflow cố định · [ ] một agent · [ ] nhiều agent — 2 dòng lý do, và vì sao **không** chọn hình dạng phức tạp hơn:
- **AI dựa vào đâu** — mỗi công cụ (khớp `codebase/tools.py`):

  | Công cụ | Input | Output | Tác động ra ngoài? |
  |---|---|---|---|
  |  |  |  |  |

- **Mức tự động:** [ ] AI gợi ý, người quyết · [ ] AI tự làm khi chắc, chuyển người khi không · [ ] AI tự làm — lý do (sai thì ai chịu gì, sửa đắt hay rẻ):
- **Chỗ chặn rủi ro** (rủi ro lớn nhất của lát cắt bị chặn ở đâu, bằng gì):
- **Chỗ người duyệt** (việc AI không được tự làm):
- **Nguyên tắc thiết kế** (≥3, bắt buộc G10):

  | Nguyên tắc | Chỗ cụ thể trên sơ đồ / trong bản chạy thử |
  |---|---|
  | G10 — thu hẹp phạm vi khi không chắc |  |
  |  |  |
  |  |  |

- Phần nào còn giả (công cụ trả dữ liệu giả, model chế độ giả…) — ghi rõ, không giả làm thật:

## §5. Chỗ khó — 4 lớp + ≥6 kịch bản + 2 tấn công *(guide 2.3)*

| Kịch bản | Lớp (1–4) | Hành vi mong muốn (nói gì, hiện gì, cho làm gì tiếp) | Câu thử |
|---|---|---|---|
|  |  |  |  |
| *(tấn công)* |  |  |  |
| *(tấn công)* |  |  |  |

(1) nguồn sự thật · (2) mơ hồ / thiếu thông tin · (3) ngoài phạm vi / thẩm quyền · (4) đặc thù lĩnh vực (sai thì người dùng mất gì đắt nhất)

## §6. Bốn đường đi của trải nghiệm
- Mọi thứ suôn sẻ: · Không chắc (lớp 2): · Không có căn cứ (lớp 1): · Người dùng sửa:
- Bị đòi ngoài phạm vi (lớp 3): · Trường hợp đặc thù lĩnh vực (lớp 4):

## §7. Đánh giá & chuẩn "đạt" *(guide 2.4, 4.1)*
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — __ câu (thuong __ · kho __ · tu_choi __) · metric: `eval/metric_spec.yaml` (__ metric)
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ __% câu qua, và __"
- Kết quả: lượt 1 __/__ (__%) · lượt 2 __/__ (__%) — run ID: __ / __ → chi tiết `eval/report.md`, hồ sơ `eval/README.md`

## §8. Chi phí khi dùng thật *(guide 4.2)*
- Persona + giá: `cost/personas.yaml` · lượt mô phỏng: `cost/simulate-__.csv` (__ phiên)
- Chi phí / task thành công: __ (model __) · __ (model __)
- Chi phí / tháng ở quy mô thật: thấp __ · cơ sở __ · cao __ → chi tiết `cost/cost-estimate.md`
- So với impact / người / tháng (§2): đáng làm không, vì sao:

## §9. Rủi ro & an toàn
- Dữ liệu: đã ẩn danh gì, không thu gì, không đưa gì vào model gói miễn phí:
- AI **không được** làm gì kể cả khi người dùng yêu cầu:
- Ai có thể bị hại nếu AI sai, và nhóm chặn thế nào:

## §10. Phân công & changelog
- Phân công có tên (theo chặng, chia cặp — guide "Cách chia việc"): __
- Dùng AI vào việc gì (2–3 dòng; chi tiết `docs/ai-usage.md`):
- Nhật ký thay đổi — **mọi thay đổi sau CP2 19:30 Thứ Sáu 27/11 phải có dòng ở đây**:

**CP2 → CP4** (vd thu hẹp lát cắt, hỏi thêm người dùng, lần cải tiến trước lượt 2)

| Thời điểm | Đổi gì | Vì sao (trỏ về câu thử / lỗi / bằng chứng nào) |
|---|---|---|
|  |  |  |

**Sau CP4 (đến 23:59 Thứ Bảy 28/11)** (sửa theo góp ý — không sửa chuẩn "đạt", câu thử, số bằng chứng, kết quả các lượt đã chạy)

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
|  |  |  |
