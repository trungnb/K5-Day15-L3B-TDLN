# Phương án & Phân công nhóm TDLN (Track B · Y tế — BS RHM)

> Tài liệu làm việc nội bộ của nhóm TDLN · Cập nhật: 2026-11-27.
> Đối chiếu theo `Guide/01-challenge-brief.md`, `Guide/02-guide.md`, `Guide/03-rubric.md` và `Guide/tracks/track-b-healthcare.md`.

---

## §A. 5 điểm rà lại kế hoạch (nêu thẳng)

1. **Bằng chứng pain (R1 — 14đ + điều kiện cứng xét giải):** Trung là BS RHM nhưng là **người trong nhóm**, nên kinh nghiệm của Trung **không tính là bằng chứng** (guide 1.1, 1.2; rubric R1). Vai trò thật của Trung là **"cửa vào"** mạng lưới BS RHM.
   - Nguồn chính: **phỏng vấn ≥3 BS RHM ngoài nhóm** (10–15 phút/người, hỏi chuyện thật trong 1 tháng qua, mỗi người 1 file `evidence/interviews/P*.md` + ≥5 trích dẫn nguyên văn bỏ tên → đạt điều kiện cứng xét giải và lấy ngay **11/14đ R1**).
   - Nguồn phụ kiểm chéo (+3đ lên **14/14đ R1**): **đào mục hỏi đáp công khai về RHM trên mạng** (`evidence/data-mining.md` + `evidence/count_qa.py`): đọc ≥40–50 câu hỏi công khai từ mục hỏi đáp bệnh viện/trang y khoa công khai, trích ≤2 câu bỏ tên, ghi link & ngày xem, và ghi rõ giới hạn *"phía BN hỏi vs phía BS xử lý"* để đối chiếu các nhóm bệnh nền/thuốc nền lặp lại nhiều nhất.
   - Ca thực tế của chính Trung chỉ ghi vào `spec.md` §1 để mô tả ngữ cảnh và **gắn nhãn rõ "người trong nhóm — không tính bằng chứng"**.
2. **Nguồn `nguoi_dung` cho bộ câu thử (R4 — bắt buộc ≥1/3 bộ câu thử):** Khi phỏng vấn, xin mỗi BS ngoài nhóm cho **2–3 tin nhắn ca bệnh viết theo đúng kiểu họ sẽ nhắn** (đã ẩn danh hoặc viết lại), rồi ghi cột `source` là `nguoi_dung: P1`, `nguoi_dung: P2`… Trung **không** được tự viết các câu này rồi gắn mã `nguoi_dung`.
3. **An toàn kép — "dual extraction" & kiểm đầu ra (chỗ chặn rủi ro ở `spec.md` §4):**
   - LLM#1 trích xuất thực thể, **đồng thời** code Python quét tất định toàn bộ tin nhắn gốc theo bảng alias (không phân biệt dấu tiếng Việt, chữ hoa/thường), rồi **lấy hợp (union)** hai kết quả. Nhờ vậy việc báo đủ cảnh báo `HIGH` không phụ thuộc vào việc LLM có trích sót thuốc hay không.
   - Sau khi LLM#2 soạn câu trả lời, Python kiểm tra lại: mọi rule `HIGH` đã khớp phải xuất hiện trong output; nếu thiếu thì code **tự động nối thêm** khối cảnh báo bắt buộc.
4. **Output luôn kèm mã quy tắc ổn định để chấm bằng code:** Mọi cảnh báo đều in kèm **mã quy tắc** (vd `[DDI-012]`, `[CR-007]`) và tên nguồn. Nhờ đó chấm được tự động bằng code: mã `HIGH` trong cột `expected` có xuất hiện trong output hay không, và mọi mã trích trong output có thật sự tồn tại trong CSV hay không. **Mã quy tắc đã cấp thì không bao giờ đánh số lại.**
5. **Chọn model & mức thinking:**
   - **Model chạy chính:** **`gemini-3.8-flash`** (tầng Vừa, có free tier để build; bảng chi phí tính theo giá từ 01/01/2027 trong `Guide/further-reading/model-prices.md`: **$1.50 vào / $7.50 ra** mỗi 1M token).
   - **Mức thinking:** để **thấp** cho LLM#1 (trích JSON) và **thấp nhất** cho LLM#2 (soạn trả lời). Lý do: phần suy luận lâm sàng khó đã giao cho bảng quy tắc tất định; LLM chỉ cần hiểu tiếng Việt viết tắt và diễn đạt mạch lạc — dùng tầng Rất lớn đắt gấp 2–10 lần mà lợi ích ít.
   - **Cặp model so sánh trong bảng chi phí R6:** `gemini-3.1-flash-lite` ($0.25 / $1.50) và `gemini-4-hydrogen` ($1.50 / $7.50).
   - **`UNVERIFIED` cần kiểm sớm:** nhóm đã có API key Gemini chưa; tên chính xác của tham số thinking và tên trường `usage` trong phản hồi API (Lĩnh bật `SHOW_RAW = True` trong `codebase/ai.py` để kiểm).
   - **Phương án dự phòng nếu không có key Gemini:** dùng OpenAI với **`gpt-5-mini`** ($0.25 / $2.00) làm model chính, so sánh với `gpt-6-luna` ($0.10 / $0.50) và `gpt-6.2-sol` ($2.00 / $10.00).
   - **Bảo mật dữ liệu với gói miễn phí:** gói miễn phí có thể dùng dữ liệu gửi lên để huấn luyện, nên **chỉ gửi ca giả lập / đã ẩn danh tuyệt đối**.

---

## §B. Phương án chốt

### Lát cắt 1 câu
> *Một bác sĩ RHM · nhắn tóm tắt ca (bệnh nền, dị ứng, thuốc đang dùng, thủ thuật dự kiến, thuốc định kê) · AI chuẩn hoá thực thể, tra tất định các bảng quy tắc có nguồn và quyết định mức cảnh báo (nguy cơ cao/chống chỉ định · thận trọng/cần kiểm tra · chưa có dữ liệu), hỏi lại khi thiếu, từ chối phần vượt thẩm quyền · bác sĩ nhận checklist trước thủ thuật và trước kê đơn, kèm cơ chế, nguồn, hướng kiểm tra/hội chẩn để tự quyết.*

### Không làm (≥3 điều khoá phạm vi & an toàn)
1. Không gợi ý thuốc thay thế cụ thể cho đơn thuốc.
2. Không tư vấn liều dùng, số ngày dùng hay cách phối hợp đơn.
3. Không khuyên tự ngưng hoặc đổi thuốc nền (chỉ gợi ý hội chẩn BS nội khoa/tim mạch hoặc dược sĩ lâm sàng).
4. Không chẩn đoán bệnh, không đọc/xử lý dữ liệu định danh của bệnh nhân thật (họ tên, SĐT, mã hồ sơ, ảnh đơn thật).

### Hình dạng giải pháp: **Workflow cố định 4 bước**
- **Vì sao không chọn Agent loop hay Multi-agent:** Sàng lọc an toàn y khoa đòi hỏi **100% recall** cho cảnh báo mức `HIGH` và chi phí cố định **≤ 2 lượt gọi LLM mỗi ca**. Agent tự quyết định thứ tự gọi tool có rủi ro bỏ sót bảng kiểm tra và tốn nhiều token vòng lặp hơn.

1. **Bước 1 — LLM#1 `extract_and_guard` (trả JSON):** Tách 5 mảng `conditions`, `allergies`, `baseline_drugs`, `planned_procedures`, `planned_drugs` + 3 cờ: `out_of_scope` (hỏi liều, đòi thuốc thay thế, hỏi ngưng thuốc nền, chẩn đoán), `needs_clarification` (kèm đúng 1 câu hỏi làm rõ), `has_pii`.
2. **Bước 2 — `normalize_entities(entities, raw_text)` (`@tool`, tất định):** Map alias → `canonical_id`, quét thêm toàn bộ `raw_text` (bỏ dấu, không phân biệt hoa/thường) rồi hợp nhất 2 nguồn; tên không khớp đưa vào `unmapped` (tuyệt đối không đoán). Thuốc không rõ vai (nền hay định kê) → đưa vào cả hai phía để không sót tương tác.
3. **Bước 3 — `check_drug_interactions(baseline, planned)` và `check_clinical_risks(conditions, allergies, baseline, planned, procedures)` (`@tool`, tất định):** Quét 100% tổ hợp, khớp theo `canonical_id` hoặc `class:<drug_class>`. Với DDI chỉ xét các cặp có **ít nhất 1 thuốc định kê**.
4. **Bước 4 — LLM#2 soạn checklist & Guard kiểm cuối:**
   - Soạn phản hồi **< 1800 ký tự**, chia rõ 4 khối: `🔴 Nguy cơ cao` / `🟡 Thận trọng` / `❔ Chưa có dữ liệu` / `🚫 Ngoài phạm vi`, cuối tin luôn có câu **"BS là người quyết định"**.
   - **Guard Python:** kiểm tra mọi `rule_id` mức `HIGH` đã khớp đều phải có mặt trong output; thiếu mã nào tự động nối thêm khối cảnh báo của mã đó.
   - Nếu `needs_clarification` và không còn thực thể hợp lệ nào để tra → hỏi lại đúng 1 câu ngắn (**G10**).
   - Nếu `has_pii` → nhắc nhở ẩn danh và **không lặp lại** thông tin định danh đó trong output.

### Hợp đồng đóng băng *(chốt lúc 11:00 — không đổi tên cột hay chữ ký hàm khi chưa báo cả nhóm)*

- **`data/entity_aliases.csv`:**
  `alias,canonical_id,display_name,entity_type,drug_class,notes,source`
  - `entity_type` ∈ `drug | condition | allergy | procedure`
  - Với `procedure`, cột `drug_class` ghi nhóm thủ thuật ∈ `invasive_bleeding | local_anesthesia | non_invasive`
- **`data/ddi_rules.csv`:**
  `rule_id,drug_a,drug_b,severity,mechanism,clinical_guidance,source`
  - `rule_id` dạng `DDI-001` · `severity` ∈ `HIGH | MODERATE`
- **`data/clinical_risk_rules.csv`:**
  `rule_id,factor_type,factor_id,target_type,target_id,severity,mechanism,clinical_guidance,source`
  - `rule_id` dạng `CR-001` · `factor_type` ∈ `condition | allergy | baseline_drug` · `target_type` ∈ `planned_drug | procedure_group`
- **Output chuẩn của mỗi tool tra cứu:** `list[dict]` với khóa `{rule_id, severity, a, b, mechanism, guidance, source}`.
- **Điểm nối duy nhất:** `answer(text: str) -> {"output": str}` trong `codebase/agent.py` (dùng chung cho `run.py`, `eval`, `simulate` và `bot/zalo_bot.py`).
- **Định dạng cột `expected` trong `eval/benchmark.csv`:**
  `HIGH: DDI-012, CR-004; MODERATE: ...; hành vi: cảnh báo|hỏi lại|từ chối|chưa có dữ liệu`

### Nguồn dữ liệu & quy tắc kiểm chứng
- Nguồn chính thống: **Quyết định 5948/QĐ-BYT**, **DDInter** (license CC BY-NC-SA 4.0 — ghi rõ trong `data/DATA_CARD.md`), **Dược thư Quốc gia Việt Nam lần 3**, hướng dẫn **SDCEP / ADA / AAOMS / AHA**.
- Mọi dòng trong 3 file CSV đều **bắt buộc có cột `source`**.
- **Lưu ý kiểm chứng:** Mọi URL và thông tin tham khảo từ file nháp (`HANDOFF.md`) phải **mở ra kiểm lại trực tiếp** trước khi đưa vào `data/DATA_CARD.md` hoặc CSV.

---

## §C. Phân công 4 thành viên

| Thành viên | Vai trò & file sở hữu riêng | CP1 (→ 17:00 nay) | CP2 (17:00 → 19:30 nay) | CP3 (tối nay → 10:00 mai) | CP4 (10:00 → 14:30 mai) |
|---|---|---|---|---|---|
| **Trung** *(BS RHM · Đội trưởng)* | **Chuyên môn RHM & nộp mốc.** Sở hữu: `clinical_risk_rules.csv` (nội dung lâm sàng), `evidence/interviews/*`, nộp form các checkpoint | Cùng Nguyên viết `evidence/hypothesis.md` và commit **trước** khi hỏi người đầu tiên; chốt lịch & bắt đầu phỏng vấn ≥3 BS RHM ngoài nhóm; nộp **Form 1 (trước 16:30)** và **Form 2 nhánh CP1 (trước 17:00)** | Viết ~15 rule `CR` v1 có nguồn; cùng Đức chấm chéo 5 output; duyệt `spec.md` §5 về mặt lâm sàng; nộp CP2 | Hoàn tất ≥3 phỏng vấn, xin mỗi BS 2–3 tin nhắn ca bệnh thực tế; duyệt từng dòng 3 file CSV và cột `expected` của bộ câu thử; nộp CP3 | Cho 2–3 BS ngoài nhóm dùng thử bot Zalo theo 5 nhịp (Nguyên ghi log); thuyết trình phần pain và lâm sàng; nộp CP4 |
| **Nguyên** *(SWE + BA)* | **BA, Dữ liệu DDI & Tích hợp Bot/Slide.** Sở hữu: `canvas.md`, `spec.md` §0–§3, §6, §10, `README.md`, `data/entity_aliases.csv`, `data/ddi_rules.csv`, `data/build/*`, `data/DATA_CARD.md`, `bot/`, `docs/zalo-bot.md`, `demo-slides.pdf` | Soạn kịch bản phỏng vấn Mom Test (`evidence/interviews/SCRIPT_MOM_TEST.md`); hỗ trợ Đức tìm link nguồn hỏi đáp RHM công khai nếu cần; viết `canvas.md`; viết `spec.md` §0–§2 với bảng Impact ≥3 hướng (RHM; người nhà sắp thuốc cho cha mẹ — B2; chat nhà thuốc — B3), số chưa có nguồn ghi rõ *(tự ước tính)*; tìm nguồn công khai số BS RHM VN (hiện chưa biết) | Viết script tất định `data/build/` lọc DDInter & QĐ 5948 theo ~20 hoạt chất RHM → `ddi_rules.csv` v1; tạo `entity_aliases.csv` v1 & `DATA_CARD.md` v1 | *(Tối nay)* chạy thử bot ở chế độ fake; hoàn thiện CSV (~80–120 alias); chép biên bản phỏng vấn của Trung vào `evidence/interviews/P*.md` | Đưa bot Zalo chạy live trước 11:30; ghi `validation/log.md` theo 5 nhịp; xuất slide 8 trang đúng file `demo-slides.pdf` ở thư mục gốc repo |
| **Lĩnh** *(Nền công nghệ)* | **AI Core & Guardrails.** Sở hữu: `codebase/ai.py`, `codebase/agent.py`, `codebase/tools.py`, prompt, `spec.md` §4 (sơ đồ) & §9 | Nối Gemini (`python3 run.py eval --try` thấy token > 0); dựng khung `agent.py` 4 bước với stub tool | Viết `tools.py` đọc 3 CSV + dual extraction; xác nhận `python3 run.py` chạy hết luồng; vẽ sơ đồ `spec.md` §4 | Hoàn thiện prompt, guard (PII, ngoài phạm vi, kiểm mã `HIGH`); chạy `eval` lượt 1 (`run-1.csv`) cùng cả nhóm; quay video 30 giây | Thực hiện 1 lần cải tiến rồi chạy `run-2.csv`; trả lời phần kỹ thuật *"vì sao chọn workflow cố định"* lúc demo |
| **Đức** *(Nền toán)* | **Eval, Số liệu & Chi phí R6.** Sở hữu: `eval/*`, `cost/*`, `spec.md` §5, §7, §8, `evidence/data-mining.md`, `evidence/qa_sample.csv`, `evidence/count_qa.py` | Cùng Trung viết 4 lớp chỗ khó + ≥6 kịch bản + 2 tấn công (`spec.md` §5); chốt nguồn & mẫu đếm trong `evidence/data-mining.md`; nháp `eval/metric_spec.yaml` | Hoàn thiện ≥12 câu `eval/benchmark.csv`; chấm chéo 5 output với Trung (khớp ≥4/5, ghi `eval/README.md`); chốt `spec.md` §7 **trước 19:15**; kiểm `python3 run.py check` sạch | Thu thập & gắn nhãn ≥40–50 câu hỏi đáp RHM công khai vào `evidence/qa_sample.csv`, chạy `evidence/count_qa.py` tính `x/N (%)` đưa vào `evidence/data-mining.md` & đối chiếu trong `evidence/summary.md`; mở rộng 24–28 câu thử (≥5 `kho`, ≥2 `tu_choi`, ≥1/3 `nguoi_dung`); viết `eval/grade.py` (chỉ in gợi ý chấm ra `eval/grade-N.md`, **không sửa** run CSV, người chấm tự điền cột `pass`); chạy `simulate --try` | Chấm `run-2.csv`; viết `eval/report.md` & `eval/README.md`; chạy `simulate --rate-from eval/run-2.csv` (≥50 phiên) → `cost/cost-estimate.md` (persona lấy tần suất từ phỏng vấn P1–P3, thiếu ghi rõ *(tự ước tính)*) |

### Đề xuất metric & chuẩn "đạt" *(Đức chốt trước 19:15 hôm nay)*
- **Metric gợi ý (`eval/metric_spec.yaml`):**
  1. `bao_du_canh_bao_nang` (code — kiểm đủ mã `HIGH` trong `expected`): **100%**
  2. `khong_bia_nguon` (code — mọi mã `[DDI-...]` / `[CR-...]` trích trong output đều tồn tại trong CSV): **100%**
  3. `tu_choi_dung` (người chấm — từ chối phần vượt thẩm quyền, không gợi ý thuốc/liều): **100% câu `tu_choi`**
  4. `hoi_lai_khi_thieu` (người chấm — hỏi lại đúng 1 câu khi thiếu thông tin cốt lõi): **≥ 80%**
  5. `bao_chua_co_du_lieu` (code — khai báo rõ mục ngoài CSDL khi có thực thể `unmapped`): **100%**
- **Chuẩn "đạt" đề xuất (`spec.md` §7):**
  *"Đạt khi ≥ 80% câu qua, **và** 100% câu có rule HIGH được báo đủ, **và** 100% câu `tu_choi` qua."*

---

## §D. Lịch đồng bộ & Luật Git

| Khung giờ | Việc đồng bộ cả nhóm |
|---|---|
| **11:00 – 11:30 hôm nay** | Chốt hợp đồng §B, viết & commit `evidence/hypothesis.md` |
| **11:30 – 16:00 hôm nay** | Chạy song song theo bảng phân công §C |
| **Trước 16:30 hôm nay** | Đội trưởng nộp **Form 1** đăng ký đội (đủ 4 MSSV, đúng khối L3B) |
| **16:00 – 17:00 hôm nay** | Ráp gói CP1 (`TEAMS.md`, `canvas.md`, `spec.md` §0–§2, `hypothesis.md`) → **Nộp CP1** |
| **17:00 – 17:20 hôm nay** | Tổng hợp bằng chứng đợt 1 + thống nhất 5 output chấm chéo |
| **19:15 hôm nay** | Chốt cứng chuẩn "đạt" `spec.md` §7 + `run.py check` → **Nộp CP2 (19:30)** |
| **Tối 27/11** | Lĩnh nối xong model thật (`eval --try` có token > 0); Nguyên chạy thử bot ở chế độ fake |
| **08:30 sáng 28/11** | Chạy `eval` lượt 1 (`run-1.csv`), chấm điểm, quay video 30 giây → **Nộp CP3 (10:00)** |
| **10:00 – 10:30 sáng 28/11** | Cả nhóm ngồi chung đọc các câu trượt `run-1` → chọn **1 cải tiến** |
| **11:30 – 13:00 trưa 28/11** | Trung + Nguyên cho BS ngoài nhóm thử bot Zalo; Lĩnh + Đức chạy `run-2.csv` (12:00) & `simulate` |
| **13:00 – 14:15 chiều 28/11** | Xuất `demo-slides.pdf` ở thư mục gốc repo, tập demo bấm giờ (Vòng 1 Zone: **5p Pitch + Demo / 3p Thử ca khó & Q&A**; lỗi mạng/API >30s bật ngay video dự phòng) → **Nộp CP4 (14:30)** |

### Luật Git tránh xung đột
- Mỗi người chỉ sửa các file thuộc quyền sở hữu của mình ở §C.
- Riêng `spec.md`: trước khi sửa phải `git pull` mới nhất và **chỉ sửa đúng mục `§` được phân công**.
- **Tuyệt đối không commit:** `.env`, `HANDOFF.md`, `bot/logs/`, `slide-kickoff-zoom-hoc-vien-k5.html`.

---

## §E. Rủi ro còn mở

1. **Chốt đủ ≥3 BS RHM ngoài nhóm để phỏng vấn:** Nếu đến **16:00 hôm nay** chưa chắc đủ đầu mối → báo ngay cho lab coach và xoay trục vai người dùng trước CP2 (19:30).
2. **Tài khoản Zalo ngoài có nhắn vào bot được không:** `UNVERIFIED` — Nguyên kiểm tra tối nay bằng một tài khoản Zalo thứ hai.
3. **API key Gemini của nhóm:** `UNVERIFIED` — cần xác nhận ngay trong phiên 11:00 để Lĩnh nối `codebase/ai.py` hoặc chuyển sang phương án dự phòng OpenAI.
