# Khảo sát nhanh BS RHM — Bộ câu hỏi Mom Test & Script tạo Google Form

- **Kênh đã gửi:** `[điền khi gửi, vd: nhóm Zalo đồng nghiệp RHM / khoa RHM]`
- **Giờ mở / giờ chốt:** `[điền khi mở và khi chốt]`
- **Link form:** `[dán link sau khi tạo]`
- **Lưu ý ẩn danh:** Tắt tự động thu thập email (`setCollectEmail(false)`). Không hỏi họ tên, mã nhân viên hay tên phòng khám (trừ câu 10 tuỳ chọn nếu người trả lời tự để lại liên hệ). Khi xuất `evidence/survey/results.csv` để commit, **bắt buộc xoá cột câu 10** (và mọi cột định danh nếu có). Bản gốc còn thông tin liên hệ lưu riêng, không commit.

---

## Thông tin đầu Form

- **Tiêu đề Form:**
  `Khảo sát nhanh (2–3 phút): Cách BS RHM rà soát bệnh nền & thuốc trước thủ thuật / kê đơn`
- **Mô tả Form:**
  `Khảo sát ẩn danh phục vụ nghiên cứu thói quen làm việc thực tế của Bác sĩ Răng Hàm Mặt khi gặp bệnh nhân có bệnh nền, thuốc đang dùng hoặc dị ứng thuốc trong 1 tháng qua. Không quảng cáo sản phẩm, không thu thập họ tên hay thông tin định danh của bác sĩ và bệnh nhân.`

---

## Bộ 10 câu hỏi (chuẩn Mom Test — hỏi hành vi đã xảy ra)

| # | Câu hỏi | Kiểu trả lời | Bắt buộc | Lựa chọn / Gợi ý điền |
|---|---|---|---|---|
| 1 | Vai trò hiện tại của anh/chị là gì? | Chọn một (`Multiple choice` + Khác) | Có | `BS RHM tại phòng khám tư` · `BS RHM tại bệnh viện / cơ sở công lập` · `BS RHM nội trú / học viên sau đại học` · `SV RHM năm cuối / thực tập lâm sàng` |
| 2 | Lần gần nhất anh/chị gặp ca bệnh nhân có bệnh nền, thuốc nền hoặc dị ứng thuốc mà phải **khựng lại kiểm tra** trước khi làm thủ thuật hoặc kê đơn là khi nào? | Chọn một (`Multiple choice`) | Có | `Hôm nay / trong tuần này` · `Trong 2–4 tuần qua` · `Hơn 1 tháng trước` · `Chưa gặp lần nào` |
| 3 | Trong **1 tháng qua**, anh/chị gặp những ca phải dừng lại rà soát như vậy khoảng bao nhiêu lần? | Chọn một (`Multiple choice`) | Có | `0 ca` · `1–2 ca` · `3–5 ca` · `6–10 ca` · `Trên 10 ca` |
| 4 | Ở lần gần nhất đó, yếu tố nào khiến anh/chị phải dừng lại kiểm tra? | Chọn nhiều (`Checkboxes` + Khác) | Không | `Thuốc chống đông / kháng kết tập tiểu cầu (Sintrom, Xarelto, Plavix, Aspirin…)` · `Tăng huyết áp / bệnh tim mạch (thuốc tê có adrenalin, chẹn beta…)` · `Đái tháo đường / thuốc hạ đường huyết` · `Loãng xương / bisphosphonate / xạ trị vùng đầu cổ` · `Dị ứng thuốc (kháng sinh, NSAID, thuốc tê…)` · `Tương tác thuốc nền với đơn định kê (kháng sinh, NSAID, corticoid…)` · `Bệnh nền khác (suy thận, suy gan, thai kỳ, hen phế quản…)` |
| 5 | Lúc đó anh/chị đã tra cứu hoặc xử lý bằng cách nào? | Chọn nhiều (`Checkboxes` + Khác) | Không | `Tra Google / web tra cứu thuốc (Drugs.com, Medscape, Dược thư…)` · `Hỏi đồng nghiệp RHM hoặc BS nội khoa / dược sĩ` · `Hỏi ChatGPT / công cụ AI khác` · `Hẹn lại BN / yêu cầu giấy xác nhận nội khoa hoặc xét nghiệm (INR, đường huyết…)` · `Chuyển tuyến` · `Đổi sang thuốc/thủ thuật an toàn hơn theo kinh nghiệm` |
| 6 | Lần gần nhất đó, khâu tra cứu / kiểm tra tốn khoảng bao nhiêu thời gian (hoặc trì hoãn)? | Chọn một (`Multiple choice`) | Có | `Dưới 5 phút` · `5–15 phút` · `15–30 phút` · `Trên 30 phút (hoặc phải hẹn buổi khác)` · `Không áp dụng (chưa gặp)` |
| 7 | Thực tế trên ghế răng, khâu nào làm anh/chị vướng nhất? | Chọn một (`Multiple choice` + Khác) | Có | `Bệnh nhân không nhớ tên thuốc / mang vỉ lẻ không rõ hoạt chất` · `Biết tên biệt dược/hoạt chất nhưng phải tra chéo rời rạc nhiều nguồn giữa ca khám gấp` · `Không chắc hướng xử trí thủ thuật (dừng thuốc nền, chỉ số INR/đường huyết, khi nào trì hoãn)` · `Cả nhận diện thuốc lẫn tra chéo tương tác đều vướng ngang nhau` · `Không thấy vướng đáng kể vì đã có quy trình cố định` |
| 8 | Cách anh/chị đang dùng để tra hiện tại có chỗ nào bất tiện hoặc khiến anh/chị lo bỏ sót nhất — và vì sao anh/chị vẫn giữ cách đó? | Đoạn văn (`Paragraph`) | Không | — |
| 9 | Nếu tiện, anh/chị có thể gõ giúp 1–2 ví dụ tóm tắt **ca bệnh giả lập đã ẩn danh** theo đúng kiểu viết tắt / tên biệt dược anh/chị hay ghi nhanh không? | Đoạn văn (`Paragraph`) | Không | Help text: *"KHÔNG nhập tên, SĐT hay mã hồ sơ thật của BN. Ví dụ: BN nam 65t rung nhĩ uống Sintrom, ĐTĐ2 uống metformin, định nhổ R48, kê Augmentin + Ibuprofen"* |
| 10 | *(Tuỳ chọn)* Anh/chị có sẵn lòng trao đổi thêm 10 phút hoặc thử nhanh bản demo 5 phút qua Zalo vào trưa mai (28/11) không? Nếu có, để lại Zalo/SĐT (bỏ trống để ẩn danh hoàn toàn). | Trả lời ngắn (`Short answer`) | Không | — |

---

## Script tạo nhanh Google Form trong 30 giây (`Google Apps Script`)

1. Mở `https://script.new` (đăng nhập tài khoản Google của bạn).
2. Xoá hết code mặc định, dán toàn bộ đoạn dưới đây vào và bấm **Save** (`Cmd+S`).
3. Chọn hàm `createRhmSurveyForm` rồi bấm **Run** → cấp quyền tạo Google Form → lấy link gửi đồng nghiệp tại **Execution log** (`Published URL`).

```javascript
function createRhmSurveyForm() {
  var form = FormApp.create(
    'Khảo sát nhanh (2–3 phút): Cách BS RHM rà soát bệnh nền & thuốc trước thủ thuật / kê đơn'
  );

  form.setDescription(
    'Khảo sát ẩn danh phục vụ nghiên cứu thói quen làm việc thực tế của Bác sĩ Răng Hàm Mặt ' +
    'khi gặp bệnh nhân có bệnh nền, thuốc đang dùng hoặc dị ứng thuốc trong 1 tháng qua. ' +
    'Không quảng cáo sản phẩm, không thu thập họ tên hay thông tin định danh của bác sĩ và bệnh nhân.'
  );
  form.setCollectEmail(false);

  // Câu 1
  form.addMultipleChoiceItem()
    .setTitle('1. Vai trò hiện tại của anh/chị là gì?')
    .setChoiceValues([
      'BS RHM tại phòng khám tư',
      'BS RHM tại bệnh viện / cơ sở công lập',
      'BS RHM nội trú / học viên sau đại học',
      'SV RHM năm cuối / thực tập lâm sàng'
    ])
    .showOtherOption(true)
    .setRequired(true);

  // Câu 2
  form.addMultipleChoiceItem()
    .setTitle(
      '2. Lần gần nhất anh/chị gặp ca bệnh nhân có bệnh nền, thuốc nền hoặc dị ứng thuốc ' +
      'mà phải khựng lại kiểm tra trước khi làm thủ thuật hoặc kê đơn là khi nào?'
    )
    .setChoiceValues([
      'Hôm nay / trong tuần này',
      'Trong 2–4 tuần qua',
      'Hơn 1 tháng trước',
      'Chưa gặp lần nào'
    ])
    .setRequired(true);

  // Câu 3
  form.addMultipleChoiceItem()
    .setTitle('3. Trong 1 tháng qua, anh/chị gặp những ca phải dừng lại rà soát như vậy khoảng bao nhiêu lần?')
    .setChoiceValues([
      '0 ca',
      '1–2 ca',
      '3–5 ca',
      '6–10 ca',
      'Trên 10 ca'
    ])
    .setRequired(true);

  // Câu 4
  form.addCheckboxItem()
    .setTitle('4. Ở lần gần nhất đó, yếu tố nào khiến anh/chị phải dừng lại kiểm tra?')
    .setChoiceValues([
      'Thuốc chống đông / kháng kết tập tiểu cầu (Sintrom, Xarelto, Plavix, Aspirin…)',
      'Tăng huyết áp / bệnh tim mạch (thuốc tê có adrenalin, chẹn beta…)',
      'Đái tháo đường / thuốc hạ đường huyết',
      'Loãng xương / bisphosphonate / xạ trị vùng đầu cổ',
      'Dị ứng thuốc (kháng sinh, NSAID, thuốc tê…)',
      'Tương tác thuốc nền với đơn định kê (kháng sinh, NSAID, corticoid…)',
      'Bệnh nền khác (suy thận, suy gan, thai kỳ, hen phế quản…)'
    ])
    .showOtherOption(true)
    .setRequired(false);

  // Câu 5
  form.addCheckboxItem()
    .setTitle('5. Lúc đó anh/chị đã tra cứu hoặc xử lý bằng cách nào?')
    .setChoiceValues([
      'Tra Google / web tra cứu thuốc (Drugs.com, Medscape, Dược thư…)',
      'Hỏi đồng nghiệp RHM hoặc BS nội khoa / dược sĩ',
      'Hỏi ChatGPT / công cụ AI khác',
      'Hẹn lại BN / yêu cầu giấy xác nhận nội khoa hoặc xét nghiệm (INR, đường huyết…)',
      'Chuyển tuyến',
      'Đổi sang thuốc/thủ thuật an toàn hơn theo kinh nghiệm'
    ])
    .showOtherOption(true)
    .setRequired(false);

  // Câu 6
  form.addMultipleChoiceItem()
    .setTitle('6. Lần gần nhất đó, khâu tra cứu / kiểm tra tốn khoảng bao nhiêu thời gian (hoặc trì hoãn)?')
    .setChoiceValues([
      'Dưới 5 phút',
      '5–15 phút',
      '15–30 phút',
      'Trên 30 phút (hoặc phải hẹn buổi khác)',
      'Không áp dụng (chưa gặp)'
    ])
    .setRequired(true);

  // Câu 7
  form.addMultipleChoiceItem()
    .setTitle('7. Thực tế trên ghế răng, khâu nào làm anh/chị vướng nhất?')
    .setChoiceValues([
      'Bệnh nhân không nhớ tên thuốc / mang vỉ lẻ không rõ hoạt chất',
      'Biết tên biệt dược/hoạt chất nhưng phải tra chéo rời rạc nhiều nguồn giữa ca khám gấp',
      'Không chắc hướng xử trí thủ thuật (dừng thuốc nền, chỉ số INR/đường huyết, khi nào trì hoãn)',
      'Cả nhận diện thuốc lẫn tra chéo tương tác đều vướng ngang nhau',
      'Không thấy vướng đáng kể vì đã có quy trình cố định'
    ])
    .showOtherOption(true)
    .setRequired(true);

  // Câu 8
  form.addParagraphTextItem()
    .setTitle(
      '8. Cách anh/chị đang dùng để tra hiện tại có chỗ nào bất tiện hoặc khiến anh/chị lo bỏ sót nhất ' +
      '— và vì sao anh/chị vẫn giữ cách đó?'
    )
    .setRequired(false);

  // Câu 9
  form.addParagraphTextItem()
    .setTitle(
      '9. Nếu tiện, anh/chị có thể gõ giúp 1–2 ví dụ tóm tắt ca bệnh giả lập đã ẩn danh ' +
      'theo đúng kiểu viết tắt / tên biệt dược anh/chị hay ghi nhanh không?'
    )
    .setHelpText(
      'KHÔNG nhập tên, SĐT hay mã hồ sơ thật của BN. ' +
      'Ví dụ: BN nam 65t rung nhĩ uống Sintrom, ĐTĐ2 uống metformin, định nhổ R48, kê Augmentin + Ibuprofen'
    )
    .setRequired(false);

  // Câu 10
  form.addTextItem()
    .setTitle(
      '10. (Tuỳ chọn) Anh/chị có sẵn lòng trao đổi thêm 10 phút hoặc thử nhanh bản demo 5 phút qua Zalo ' +
      'vào trưa mai (28/11) không? Nếu có, để lại Zalo/SĐT (bỏ trống để ẩn danh hoàn toàn).'
    )
    .setRequired(false);

  Logger.log('Published URL (gửi đồng nghiệp): ' + form.getPublishedUrl());
  Logger.log('Edit URL (để chỉnh sửa / xem kết quả): ' + form.getEditUrl());
}
```
