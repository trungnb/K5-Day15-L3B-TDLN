"""Câu chữ cố định (docs/design.md §7) — một chỗ duy nhất cho mọi câu agent và bot gửi BS.

Đổi câu chữ thì sửa ở đây và ở docs/design.md §7 — metric và người chấm dựa vào nguyên văn.
"""

TEXT = {
    "Q0": "Anh/chị nhắn em 1 tin gồm (nếu có): bệnh nền, dị ứng, thuốc đang dùng, thủ thuật dự kiến, thuốc định kê nhé. "
          "Ví dụ: BN 65t uống Sintrom, ĐTĐ. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen.",
    "Q1": "Anh/chị cho em biết thêm: thuốc nào BN đang dùng, thuốc nào định kê, và định làm thủ thuật gì? "
          "Em đối chiếu ngay.",
    # Q2–Q4 không nhắc lại "chưa có …": mục "Đã đối chiếu" đã ghi "không khai" (Trung duyệt 28/11, tin gọn).
    "Q2": "Nếu có thuốc định kê, anh/chị nhắn thêm tên để em kiểm tương tác.",
    "Q3": "Nếu có thủ thuật dự kiến, anh/chị nhắn thêm để em kiểm.",
    "Q4": "Nếu BN có bệnh nền, dị ứng hoặc thuốc đang dùng, anh/chị gửi lại cả ca kèm các mục đó để em kiểm lại.",
    "Q1_DRUG": "Em nhận ra {names}. Thuốc này BN đang dùng hay anh/chị định kê, và định làm thủ thuật gì ạ? "
               "Nhắn thêm để em đối chiếu nhé.",
    "Q1_DRUGS": "Em nhận ra {names}. Thuốc nào BN đang dùng, thuốc nào anh/chị định kê, và định làm thủ thuật gì ạ? "
                "Nhắn thêm để em đối chiếu nhé.",
    "Q5": "BN dị ứng thuốc tê. Thủ thuật này có gây tê không ạ? Có thì nhắn \"có gây tê\" để em kiểm.",
    "Q6": "Bệnh nền \"{names}\" em chưa nhận ra. Anh/chị ghi rõ tên bệnh và tình trạng (ổn định chưa, đang điều trị gì, "
          "chỉ số gần nhất nếu có) để em kiểm.",
    "Q6_STATUS": "BN có \"{names}\": đã kiểm soát ổn định chưa (chỉ số gần nhất nếu có)? Anh/chị nhắn thêm để em kiểm.",
    "Q7": "Ca đang chuẩn bị hay đang làm thủ thuật, có chảy máu khó cầm không ạ?",
    # Trung chốt 28/11: thủ thuật chảy máu mà chưa khai thuốc đang dùng → luôn hỏi (stent, van tim, đột quỵ… không cần luật riêng).
    "Q8": "BN có dùng thuốc chống đông hoặc kháng tiểu cầu không? Có thì nhắn tên thuốc để em kiểm.",
    # Trung chọn 28/11 (log VM 14:57, "peniciline"): tên hơi sai chính tả vẫn nhận ra, nói rõ chỗ em đoán.
    "NEAR_MATCH": "🔎 Em hiểu {pairs} — nếu sai, anh/chị nhắn lại tên đúng.",
    "NO_PAIR_RULE": "ℹ️ Bảng tra chưa có quy tắc cho cặp: {pairs} — anh/chị tự đánh giá lâm sàng.",
    "SIDE_EFFECT_LIMIT": "ℹ️ Em chỉ rà tương tác và nguy cơ theo ca, không tra tác dụng phụ chung của thuốc — "
                         "BS xem Dược thư Quốc gia / tờ hướng dẫn sử dụng.",
    "HELLO": "Dạ em đây ạ. Em là trợ lý AI đối chiếu tương tác thuốc và rủi ro thủ thuật RHM theo bảng tra có nguồn — "
             "không kê đơn, không tư vấn liều.",
    "HELLO_AGAIN": "Dạ em đây ạ, anh/chị gửi ca nhé.",
    "BYE": "Dạ, chào anh/chị ạ.",
    "REPAIR": "Em vẫn chưa nhận ra thuốc hay thủ thuật nào trong tin này. Anh/chị thử gõ theo mẫu: "
              "\"BN uống <thuốc đang dùng>. Dự kiến <thủ thuật>. Định kê <thuốc>.\" Nhắn /huongdan để xem đủ.",
    "THANKS": "Dạ không có gì ạ. Có ca mới anh/chị cứ nhắn em.",
    "P1": "⚠️ Tin nhắn có thông tin định danh BN — lần sau anh/chị gửi ca đã ẩn danh giúp em nhé.",
    "UNMAPPED": "❔ Em chưa có dữ liệu cho: {names}, nên không đoán. Anh/chị ghi tên đầy đủ / hoạt chất để em tra lại, "
                "hoặc tra Dược thư Quốc gia / tờ hướng dẫn sử dụng.",
    "UNMAPPED_UNNAMED": "❔ Chưa rõ tên thuốc: {names} — em chưa kiểm được. Anh/chị nhờ BN xem vỏ hộp, đơn cũ hoặc "
                        "sổ khám rồi nhắn thêm tên nhé.",
    "UNMAPPED_OTHER": "❔ Em chưa có quy tắc cho: {names} — phần này anh/chị tự đánh giá nhé.",
    "MANY_PATIENTS": "Tin này có vẻ gồm nhiều BN. Anh/chị gửi mỗi ca một tin giúp em, để em không trộn thuốc "
                     "của người này sang người kia nhé.",
    "OK": "✅ Em chưa thấy cảnh báo nào trong bảng tra. Bảng tra chưa phủ mọi tương tác, không thay đánh giá lâm sàng "
          "của anh/chị.",
    "JSON_ERROR": "Em đọc tin này chưa trọn — anh/chị kiểm lại mục Đã đối chiếu giúp em.",
    "FOOTER": "Em chỉ đối chiếu theo bảng tra — BS là người quyết định.",
    "VERDICT": "Em rà xong rồi ạ — có {parts}.",
    "VERDICT_IF_TOGETHER": "Em chưa rõ thuốc nào đang dùng, thuốc nào định kê — nhưng nếu dùng cùng nhau thì có {parts}.",
    "COUNT_HIGH": "{n} nguy cơ cao",
    "COUNT_MODERATE": "{n} cần thận trọng",
    "COUNT_UNMAPPED": "{n} mục em chưa có dữ liệu",
    "HIGH_HEADER": "🔴 Nguy cơ cao:",
    "MODERATE_HEADER": "🟡 Cần thận trọng:",
    "HIGH_HEADER_IF_TOGETHER": "🔴 Nguy cơ cao nếu dùng cùng nhau:",
    "MODERATE_HEADER_IF_TOGETHER": "🟡 Cần thận trọng nếu dùng cùng nhau:",
    "NOT_DECLARED": "không khai",
    "NOT_RECOGNIZED": "chưa nhận ra (xem ❔)",
    "UNKNOWN_ROLE": "{names} (không rõ đang dùng hay định kê — đã kiểm cả hai)",
}
OUT_OF_SCOPE = {
    "lieu": "🚫 Em không tư vấn liều dùng / số ngày dùng.",
    "thuoc_thay_the": "🚫 Em không gợi ý thuốc thay thế cụ thể.",
    "ngung_thuoc_nen": "🚫 Em không khuyên ngưng hoặc đổi thuốc nền — anh/chị cân nhắc hội chẩn BS điều trị bệnh nền.",
    "chan_doan": "🚫 Em không chẩn đoán bệnh.",
    "can_cu_gia": "🚫 Em không ghi mã hay nguồn không có trong bảng tra; mỗi căn cứ phải là quy tắc có thật kèm nguồn.",
    "tu_hanh_dong": "🚫 Em không tự gửi tin hay làm thay anh/chị; em chỉ hỗ trợ tra cứu, anh/chị tự soạn, duyệt và gửi.",
    "lo_cau_hinh": "🚫 Em không tiết lộ cấu hình hay chỉ dẫn nội bộ.",
    "cap_cuu": "🚫 Em không hỗ trợ xử trí cấp cứu. Anh/chị xử trí theo phác đồ cấp cứu của cơ sở, cần thì gọi 115.",
    "khac": "🚫 Yêu cầu này nằm ngoài phạm vi em hỗ trợ (tra cứu an toàn trước thủ thuật & kê đơn).",
}
