# Thiết kế bản chạy thử — Trợ lý kiểm tra an toàn RHM (TDLN)

> Bản thiết kế chi tiết để cả nhóm code theo. `spec.md` §4 chỉ tóm tắt và trỏ về file này.
> Người giữ file: Lĩnh. Bản nháp v0.1 · 27/11/2026. Mục ⚠️ là chỗ **cần người được nêu tên xác nhận** trước khi code phần đó.
> Thay đổi so với `docs/team-plan.md` §B: xem §12.

**Đọc phần nào:**

| Bạn làm | Đọc |
|---|---|
| `agent.py`, `tools.py`, `ai.py` (Lĩnh) | Tất cả |
| CSV, `data/build/` (Nguyên) | §1, §3, §4.3, §5 bước 2–3, §11 |
| Bot Zalo (Nguyên, Lĩnh) | §1, §4.1, §9 |
| Bộ câu thử, metric (Đức) | §1, §6, §7, §10 |
| Duyệt lâm sàng (Trung) | §1, §7, §11 |

---

## 1. Tóm tắt một trang

- **Lát cắt:** một BS RHM nhắn tóm tắt ca (bệnh nền, dị ứng, thuốc đang dùng, thủ thuật dự kiến, thuốc định kê) → nhận checklist cảnh báo kèm mã quy tắc và nguồn → BS tự quyết.
- **Hình dạng:** workflow cố định, **tối đa 2 lần gọi model mỗi ca**. Không dùng agent tự chọn bước, vì bước tra bảng phải luôn chạy (không được sót cảnh báo HIGH) và chi phí phải cố định.
- **Chia việc AI / code:**
  - Model làm việc nó giỏi: đọc tin nhắn tiếng Việt viết tắt (bước 1), diễn đạt lại cảnh báo cho gọn (bước 4).
  - Code làm mọi việc phải đúng 100%: đổi tên thuốc, tra bảng, quyết định đi nhánh nào, kiểm đủ mã HIGH, ráp tin trả lời.
- **Nguyên tắc thiết kế:**

| Nguyên tắc | Ở đâu trong luồng |
|---|---|
| G10 — thu hẹp phạm vi khi không chắc | Tên lạ → khối ❔ "Chưa có dữ liệu", không đoán. Thiếu thủ thuật lẫn thuốc định kê → hỏi lại, không tra bừa. Không phát hiện gì → nói "không phát hiện trong bảng tra", **không bao giờ nói "an toàn"** |
| Không phụ thuộc một mình model ở chỗ nguy hiểm | Bước 2 code quét lại tin gốc; sau bước 4 code kiểm đủ mã HIGH |
| AI gợi ý, BS quyết | Không kê đơn, không tư vấn liều, không gợi ý thuốc thay thế, không khuyên ngưng thuốc nền. Câu cuối luôn là "BS là người quyết định." |
| Truy được nguồn | Mọi cảnh báo in mã quy tắc (`[DDI-001]`, `[CR-001]`) và nguồn; mã không bao giờ đánh số lại |

---

## 2. Kiến trúc

```mermaid
flowchart LR
  subgraph IN[Lối vào]
    R1[python run.py]
    R2[run.py eval]
    R3[run.py simulate]
    B[bot/zalo_bot.py]
  end
  Z[(Zalo)] -. long polling .-> B
  R1 & R2 & R3 & B -->|text| AG[codebase/agent.py<br/>answer&#40;text&#41;]
  AG -->|≤ 2 lần/ca| AI[codebase/ai.py<br/>call_model]
  AI -->|HTTPS| G[(Gemini API)]
  AG -->|@tool| T[codebase/tools.py]
  T -->|đọc| D[(data/*.csv)]
  AI -. ghi .-> TR[codebase/tracing.py<br/>khung BTC]
  T -. ghi .-> TR
  TR --> O[traces/ · eval/run-N.csv · cost/]
```

| File | Người | Làm gì | Ghi chú |
|---|---|---|---|
| `codebase/agent.py` | Lĩnh | `answer(text)`: chạy luồng §3, ráp tin trả lời | Điểm nối duy nhất cho run.py, eval, simulate, bot |
| `codebase/tools.py` | Lĩnh | 3 công cụ ở §4.4, đều tất định, không tác động ra ngoài | |
| `codebase/ai.py` | Lĩnh | `call_model(system, user)` → `{text, model, tokens_in, tokens_out}` | Chỗ duy nhất gọi model |
| `data/*.csv`, `data/build/` | Nguyên (nội dung lâm sàng: Trung) | Dữ liệu và script dựng/kiểm | Xem §4.3 |
| `bot/zalo_bot.py` | Nguyên; phần ghép tin (§9): Lĩnh, làm sau | Lớp vỏ: nhận tin → `answer()` → gửi | Không chứa logic tra cứu |
| `codebase/tracing.py`, `run.py`, `eval/run_eval.py`, `cost/simulate.py` | Khung BTC | **Không sửa** | |

---

## 3. Luồng xử lý một tin nhắn

```mermaid
flowchart TD
  A([Tin nhắn ca bệnh của BS]) --> S1["1 · Model lần 1 (AI)<br/>trích 5 trường + 2 cờ"]
  A -. tin gốc .-> S2
  S1 -->|JSON| S2["2 · Chuẩn hoá + quét lại tin gốc (code)"]
  CA[(entity_aliases.csv)] --> S2
  S2 --> D1{"Có thủ thuật hoặc<br/>thuốc định kê?"}
  D1 -->|thiếu cả hai| Q["Câu cố định: hỏi lại /<br/>hướng dẫn / từ chối"]
  Q -. "BS nhắn bổ sung → bot ghép tin cũ" .-> A
  D1 -->|có ít nhất một| S3["3 · Tra bảng quy tắc (code)"]
  CR[(ddi_rules.csv<br/>clinical_risk_rules.csv)] --> S3
  S3 --> D2{"Có rule nào khớp?"}
  D2 -->|không: bỏ qua model 2| R
  D2 -->|có| S4["4 · Model lần 2 (AI)<br/>viết khối 🔴 🟡"]
  S4 --> D3{"Đủ mọi mã HIGH?"}
  D3 -->|thiếu| GD["Code nối cảnh báo còn thiếu"]
  GD --> R
  D3 -->|đủ| R["5 · Ráp tin trả lời (code)"]
  S1 -. "2 cờ: vượt quyền, có PII" .-> R
  R --> O([Tin gửi BS])

  classDef ai fill:#e7effd,stroke:#1d5bd8
  classDef guard fill:#fdeceb,stroke:#cf2a1f
  class S1,S4 ai
  class S2,D3,GD guard
```

Model chỉ có ở 2 ô xanh. Mọi hình thoi là if/else trong code. Ô đỏ là lớp bảo hiểm.

---

## 4. Hợp đồng giữa các phần

### 4.1 `answer(text)` — dùng chung cho run.py, eval, simulate, bot

```python
answer(text: str) -> {"output": str, "needs_more": bool}
answer(text: str, detail=True)   # (28/11) chỉ bot gọi, cho lệnh "chi tiết": in đủ hướng xử trí của 🟡
```

- `output`: tin trả lời hoàn chỉnh, mục tiêu ≤ 1800 ký tự (Zalo giới hạn 2000/tin; bot tự cắt nếu dài hơn).
- `needs_more`: `True` khi tin trả lời mời BS nhắn bổ sung thủ thuật/thuốc định kê (§6). Bot dùng khoá này để ghép tin (§9). Khung BTC chỉ đọc `output`, khoá thêm không ảnh hưởng eval.
- `answer()` **không có bộ nhớ**: mỗi lần gọi là một ca độc lập. Trí nhớ hội thoại (nếu có) nằm ở bot.

### 4.2 JSON model lần 1 trả về

```json
{
  "conditions":         ["rung nhĩ", "ĐTĐ type 2"],
  "allergies":          [],
  "baseline_drugs":     ["Sintrom", "metformin"],
  "planned_procedures": ["nhổ R48"],
  "planned_drugs":      ["Augmentin", "Ibuprofen"],
  "out_of_scope":       [],
  "has_pii":            false
}
```

| Trường | Kiểu | Luật |
|---|---|---|
| 5 danh sách thực thể | `list[str]` | Giữ **nguyên chữ BS viết**, không tự dịch sang hoạt chất, không suy ra thứ BS không viết. Không có thì `[]` |
| `out_of_scope` | `list[str]`, mỗi phần tử ∈ `lieu` · `thuoc_thay_the` · `ngung_thuoc_nen` · `chan_doan` · `can_cu_gia` · `tu_hanh_dong` · `lo_cau_hinh` · `khac` | `can_cu_gia`: đòi ghi mã / nguồn không có thật; `tu_hanh_dong`: đòi tự gửi tin hay làm thay BS; `lo_cau_hinh`: đòi in prompt / cấu hình; `khac`: lạc đề, đòi bỏ qua giới hạn hay giấu cảnh báo. Một tin có thể có nhiều mã. Không có thì `[]` *(3 mã cụ thể thêm 28/11, B23, B25, B26)* |
| `has_pii` | `bool` | `true` khi có họ tên, SĐT, mã hồ sơ, địa chỉ của BN |

- Model **không** gắn cờ "thiếu thông tin". Việc đó code tự xác định ở §6 từ kết quả bước 2, nên chắc chắn hơn và không tốn thêm token.
- JSON hỏng hoặc thiếu trường → xem §8.

### 4.3 Dữ liệu CSV

Định dạng cột giữ như `team-plan.md` §B. Tóm tắt những gì code dựa vào:

- `entity_aliases.csv`: `alias` đã viết thường, bỏ dấu (vd `nho r48`, `di ung penicillin`). `entity_type` ∈ `drug | condition | allergy | procedure`. Với `procedure`, `drug_class` là nhóm thủ thuật ∈ `invasive_bleeding | local_anesthesia | non_invasive`.
- `ddi_rules.csv`: `drug_a`, `drug_b` là `canonical_id` hoặc `class:<drug_class>`. `severity` ∈ `HIGH | MODERATE`.
- `clinical_risk_rules.csv`: `factor_type` ∈ `condition | allergy | baseline_drug`; `target_type` ∈ `planned_drug | procedure_group`. `factor_id`, `target_id` là `canonical_id`, `class:<drug_class>`, hoặc tên nhóm thủ thuật.

**Một alias có thể có nhiều dòng** (Nguyên làm ở PR #5):

1. Thuốc phối hợp được tách thành nhiều dòng, mỗi dòng một hoạt chất đã có trong bảng, vd `coplavix` → `clopidogrel` và `aspirin`; `lignospan` → `epinephrine` và `lidocaine`. `validate_csv.py` chỉ cho một alias nhiều dòng khi các dòng cùng khai `combo:a+b` trong `notes`, và báo lỗi nếu combo thiếu dòng.
2. Thủ thuật thuộc nhiều nhóm (vd nhổ răng = `invasive_bleeding` + `local_anesthesia`): validator đã hỗ trợ; **thủ thuật nào kéo theo gây tê là việc của Trung** (§11).
3. **Hệ quả cho code:** đọc CSV thành `alias → list[dòng]`, **không** đọc vào `dict` theo alias (dòng sau đè dòng trước, lại sót aspirin). Code không đọc cột `notes` để suy ra thành phần; dữ liệu đã tách sẵn.

### 4.4 Công cụ (`tools.py`)

Tất cả tất định, không gọi model, không tác động ra ngoài.

| Công cụ | Input | Output |
|---|---|---|
| `normalize_entities(extracted, raw_text)` | JSON §4.2 (hoặc `None` nếu model lỗi) + tin gốc | `{"conditions", "allergies", "baseline_drugs", "planned_drugs", "procedure_groups", "unknown_role_drugs", "unmapped", "checked"}`: các danh sách thực thể chuẩn `{canonical_id, display_name, drug_class}`; `unknown_role_drugs` là thuốc code tìm thêm mà không rõ vai; `unmapped` là chữ BS viết mà không có trong bảng; `checked` là danh sách để in dòng "Đã đối chiếu" |
| `check_drug_interactions(baseline_drugs, planned_drugs)` | 2 danh sách thực thể chuẩn | `list[{rule_id, severity, a, b, mechanism, guidance, source}]` (đúng hợp đồng team-plan) |
| `check_clinical_risks(conditions, allergies, baseline_drugs, planned_drugs, procedure_groups)` | Các danh sách thực thể chuẩn | Như trên |

### 4.5 Input của model lần 2

Code gửi cho model một khối JSON gồm các rule đã khớp (đã gộp theo `rule_id`, §5 bước 3), mỗi rule có `rule_id`, `severity`, tên hai phía đã khớp, `mechanism`, `guidance`, `source`. Model chỉ trả **phần thân khối 🔴 và 🟡** theo khung §7. Mọi phần khác của tin trả lời do code ráp.

---

## 5. Luật từng bước

**Bước 1 — Model lần 1.** Prompt yêu cầu: chỉ trích những gì BS viết, giữ nguyên chữ, trả đúng JSON §4.2, không giải thích. Không đưa bảng CSV vào prompt.
- **Xếp vai thuốc:** chỉ đưa thuốc vào `planned_drugs` khi tin nói rõ là định kê ("kê", "định kê", "cho uống", "định cho"). Mọi thuốc khác, kể cả khi không rõ vai, đưa vào `baseline_drugs`. Vì vậy tin chỉ liệt kê tên thuốc mà không nói thuốc nào định kê (vd "Cordarone, Klacid, Dexa — check tương tác") sẽ không có thuốc định kê, rơi vào tình huống 3 ở §6 → hỏi lại Q1. Không thêm trường JSON cho thuốc không rõ vai.

**Bước 2 — Chuẩn hoá và quét lại (code).**
1. Chuẩn hoá chuỗi: viết thường, bỏ dấu tiếng Việt, gộp khoảng trắng (giống cách `alias` đã được viết).
2. Tra từng chuỗi model trả về: tìm **alias nằm trong chuỗi**, không đòi khớp nguyên chuỗi (vd "nhổ R48" → `nho r48`). Không tìm thấy alias nào → đưa nguyên chữ vào `unmapped`.
3. Quét **tin gốc** tìm mọi alias (khớp theo ranh giới từ).
4. **Ưu tiên khớp dài nhất, không chồng lấn:** `di ung ibuprofen` (dị ứng) che `ibuprofen` (thuốc), để dị ứng ibuprofen không bị coi là kê ibuprofen.
5. Gộp: thực thể code tìm thấy mà model không có →
   - thuốc: không rõ vai → thêm vào **cả** `baseline_drugs` và `planned_drugs`, đồng thời ghi vào `unknown_role_drugs` để tin trả lời có ghi chú;
   - bệnh nền, dị ứng, thủ thuật: **chỉ thêm khi model lỗi** (JSON hỏng). Khi model đọc được tin thì tin theo model, vì quét chữ không hiểu câu phủ định — vd "chưa ghi có gây tê hay không" (B22) sẽ bị hiểu thành có gây tê, "nay ghé khám răng" thành một thủ thuật. *(Sửa 27/11 sau khi chạy thử 27 câu với model thật.)*
   - Khi so khớp, bỏ từ đệm "một", "cái", "chiếc"… để "nhổ một răng" vẫn khớp `nho rang` (B01).
6. Một alias nhiều dòng (§4.3) → lấy tất cả các dòng. Thủ thuật → đưa `drug_class` vào `procedure_groups`.

**Bước 3 — Tra bảng (code).**
- Một thực thể khớp `X` khi `X == canonical_id` hoặc `X == "class:" + drug_class`.
- DDI: xét mọi cặp `(p, q)` với `p` thuộc thuốc định kê, `q` thuộc (thuốc đang dùng ∪ thuốc định kê), `p ≠ q`, khớp theo cả hai chiều `drug_a/drug_b`.
- CR: `factor_type` chọn danh sách bên trái (`condition` → bệnh nền, `allergy` → dị ứng, `baseline_drug` → thuốc đang dùng); `target_type` chọn bên phải (`planned_drug` → thuốc định kê, `procedure_group` → nhóm thủ thuật).
- **Gộp theo `rule_id`:** một rule theo nhóm có thể khớp nhiều cặp (vd `DDI-001` khớp cả Ibuprofen và Diclofenac với Sintrom) → giữ một mục, liệt kê mọi cặp.
- Sắp xếp: HIGH trước MODERATE, rồi theo `rule_id`.
- **Tình huống 3 (§6, chỉ liệt kê thuốc, chưa rõ vai):** vẫn tra DDI giữa **mọi cặp** thuốc đã nêu, và in là cảnh báo **có điều kiện** ("nếu dùng cùng nhau"); không tra CR, không tự gán vai. Khớp B04–B07 ("hỏi lại vai trò **hoặc** cảnh báo có điều kiện"). *(28/11, rà thiết kế: trước đây ca "Cordarone, Klacid, Dexa" chỉ nhận Q1 dù bảng có `DDI-013`, `DDI-023` HIGH.)*

**Bước 4 — Model lần 2.** Chỉ chạy khi có ít nhất 1 rule khớp. Prompt yêu cầu: chỉ diễn đạt lại các rule được đưa vào, không thêm kiến thức, không nêu liều, không dùng chữ "an toàn"; mỗi rule một dòng, mở đầu bằng mã `[rule_id]`, **hướng xử trí đứng trước, lý do sau**, giữ nguyên mọi con số / ngưỡng của guidance. Model nhận tên ngắn (bỏ phần chú thích trong ngoặc).

**Kiểm từng dòng model (code).** Một dòng model chỉ được dùng khi: mở đầu đúng `[rule_id]` và chỉ có mã đó; ≤ 400 ký tự; không chữ cấm, không mẫu liều; **mọi con số trong dòng đều có trong quy tắc** (chặn số bịa); với rule HIGH, **giữ đủ mọi con số của guidance** (vd ngưỡng INR của `CR-001`). Sai một điều → code dùng khung dự phòng §7 cho dòng đó. *(28/11)*

**Kiểm đủ mã HIGH (code).** Với mỗi rule HIGH ở bước 3: chuỗi `[rule_id]` không có trong output của model → code nối một dòng theo mẫu §7 vào cuối khối 🔴. Không gọi model viết lại.

**Bước 5 — Ráp tin (code).** Theo thứ tự và câu chữ ở §7.

---

## 6. Bảng quyết định: thiếu thông tin và ngoài phạm vi

"Có thủ thuật" = `procedure_groups` khác rỗng **hoặc** model có trả `planned_procedures` (kể cả chữ lạ vào `unmapped`). "Có thuốc định kê" tính tương tự. Như vậy BS đã ghi một thuốc lạ thì hệ thống báo ❔ chứ không hỏi lại "định kê thuốc gì?".

| # | Tình huống | Hành vi | `needs_more` |
|---|---|---|---|
| 0 | *(28/11)* **Cả tin** chỉ là xã giao: chào / hỏi bot làm được gì / cảm ơn, ok / tạm biệt (code so khớp sau khi bỏ dấu, dấu câu, từ đệm; tin ≤ 60 ký tự; "có", "không", "dạ" trơn **không** tính vì có thể là câu trả lời Q5) | Không gọi model. Chào / hỏi → HELLO + Q0 (bot đổi lần chào lại trong 12 giờ thành HELLO_AGAIN, §9); cảm ơn → THANKS; tạm biệt → BYE. Không câu chốt | `False` |
| 0b | *(28/11)* Tin đánh số ≥ 2 BN khác nhau ("BN1 … BN2 …", "Ca 1: … Ca 2: …") | Không gọi model. MANY_PATIENTS (xin gửi mỗi ca một tin) + câu chốt — để không trộn thuốc hai người vào một ca | `False` |
| 1 | Không có thực thể nào, không có cờ (vd "nhờ rà tương tác nhưng chưa ghi tên thuốc", "em ơi") | Gửi câu hỏi Q1 (hỏi thuốc đang dùng, thuốc định kê, thủ thuật). Q0 dùng ở tình huống 0 (sau HELLO) | `True` |
| 2 | Không có thực thể nào, có `out_of_scope` | Gửi khối 🚫 + câu hỏi Q1 (xin tên thuốc / thủ thuật) | `False` |
| 3 | Có bệnh nền/dị ứng/thuốc nền, nhưng **thiếu cả** thủ thuật và thuốc định kê | Gửi câu hỏi Q1 — có thuốc nhận ra thì dùng Q1_DRUG / Q1_DRUGS nêu thẳng tên thuốc *(28/11)*; có `out_of_scope` thì thêm khối 🚫. Có ≥ 2 thuốc thì tra DDI giữa các thuốc đã nêu và in cảnh báo có điều kiện (§5 bước 3); không tra CR *(28/11)* | `True` |
| 4 | Có thủ thuật, thiếu thuốc định kê | Chạy đủ luồng, cuối tin thêm câu nhắc Q2 | `True` |
| 5 | Có thuốc định kê, thiếu thủ thuật | Chạy đủ luồng, cuối tin thêm câu nhắc Q3 | `True` |
| 6 | Có cả hai | Chạy đủ luồng | `False` |

**Cột thứ hai — bệnh nền, dị ứng, thuốc đang dùng.** Áp dụng thêm cho tình huống 4, 5, 6:

| Bệnh nền / dị ứng / thuốc đang dùng | Hành vi | `needs_more` |
|---|---|---|
| Có ít nhất một | Không nhắc gì thêm; nhóm nào trống thì mục "Đã đối chiếu" ghi "không khai" | Theo bảng trên |
| **Thiếu cả ba** | Thêm câu nhắc Q4 (mời BS **gửi lại cả ca**); mục "Đã đối chiếu" ghi "không khai" cho cả ba | Theo bảng trên — Q4 **không** bật `needs_more` *(28/11: bật thì bot giữ ca 10 phút và có thể ghép nhầm ca BN kế tiếp vào ca khoẻ mạnh vừa xong)* |

- Không hỏi lại khi thiếu 3 trường này: hệ thống không phân biệt được BN thật sự không có với BS quên ghi, và BN khoẻ mạnh đi nhổ răng khôn là ca phổ biến. Vẫn tra được tương tác giữa các thuốc định kê với nhau (vd `DDI-006` ibuprofen + ketorolac).
**Dị ứng thuốc tê (Q5, thêm 27/11 cho B22).** Áp dụng cho tình huống 4, 5, 6: BN có dị ứng thuốc tê (`local_anesthetic`) mà không thủ thuật nào thuộc nhóm `local_anesthesia` (vd lấy cao dưới nướu — Trung chốt chỉ nhổ răng, implant, phẫu thuật nha chu tự kéo theo gây tê; 28/11 thêm rạch/chích/trích/dẫn lưu áp xe và chữa/điều trị/lấy tủy, nội nha) → nối câu Q5, `needs_more = True`, và **không** in ✅. Q5 dặn BS nhắn "có gây tê" *(28/11: "có" trơn không khớp alias thủ thuật nào nên ghép xong vẫn hỏi lại)*; BS nhắn vậy thì bot ghép tin, thủ thuật gây tê được thêm và `CR-010` khớp.

**Cải tiến lượt 2 (28/11, nhóm lỗi "không chỉ rõ phần còn thiếu": B11, B12, B13, B15 ở `eval/run-1.csv`).** Code phát hiện bằng so khớp chữ đã chuẩn hoá, không thêm lần gọi model:
- **Q7:** tin có "đang nhổ", "trong quá trình nhổ", "trong khi nhổ", "đang chảy máu" hoặc "đang làm thủ thuật" (từ ngay trước là "không/chưa/ko" thì bỏ qua) và có thủ thuật nhóm `invasive_bleeding` → hỏi giai đoạn và chảy máu khó cầm; không in ✅.
- **Q6:** bệnh nền model trích được nhưng bảng không có → hỏi tên bệnh và tình trạng hiện tại; không in ✅.
- **ℹ️ cặp thuốc:** có thuốc định kê đã nhận ra mà cả ca không khớp rule DDI nào → nêu tối đa 3 cặp chưa có quy tắc; không in ✅.
- **ℹ️ tác dụng phụ:** tin có "tác dụng phụ" → nêu giới hạn tra cứu (cả ở tình huống 3).

- Q4 có mục đích chặn trường hợp BS quên ghi thuốc nền mà nhận ✅, rồi yên tâm nhầm. Thiếu một hoặc hai trong ba trường thì không nhắc, để tin trả lời không bị quá nhiều câu nhắc.

- *(28/11)* Thuốc ❔ mà chữ BS viết là tên chung / không nhớ tên ("thuốc chống đông không nhớ tên", "thuốc huyết áp") → câu UNMAPPED_UNNAMED và `needs_more = True` để BS hỏi BN rồi nhắn tên thuốc vào cùng ca (P5: "bệnh nhân không nhớ tên thuốc").
- *(28/11)* Cờ `cap_cuu` (chảy máu không cầm, khó thở, sốc phản vệ…) → câu 🚫 `cap_cuu` đứng **đầu** tin; luồng vẫn tra tiếp; không in ✅; bỏ cờ `khac` đi kèm (model thật hay trả cả hai).
- Cờ `out_of_scope` **không làm dừng luồng**: hỏi liều vẫn tra tiếp để BS không mất cảnh báo chảy máu; code chỉ thêm khối 🚫.
- Cờ `has_pii` → thêm câu nhắc P1 ở đầu tin; tin trả lời không nhắc lại thông tin định danh (khối "Đã đối chiếu" chỉ in tên thuốc, bệnh, thủ thuật).

---

## 7. Ráp tin trả lời và câu cố định

**Thứ tự khối** (khối nào rỗng thì bỏ) — *đổi 28/11: kết luận lên đầu, "Đã đối chiếu" xuống cuối, để BS thấy ngay cần làm gì*:

1. P1 — nhắc ẩn danh (nếu `has_pii`); dòng JSON_ERROR (nếu model 1 hỏng)
2. **Kết luận** — code đếm: "Em rà xong rồi ạ — có {n} nguy cơ cao, {n} cần thận trọng, {n} mục em chưa có dữ liệu." Tình huống 3 dùng câu có điều kiện. Không có rule → bỏ dòng này (✅ đứng đầu)
3. ✅ — chỉ khi 🔴 🟡 ❔ 🚫 đều rỗng và không hỏi Q5 — code
4. 🔴 Nguy cơ cao — model viết + dòng code nối thêm
5. 🟡 Cần thận trọng — *(28/11, Trung duyệt)* dòng gọn do code viết, không gọi model 2: mã + cặp + câu đầu của cơ chế (nguyên văn bảng tra) + nguồn; không in hướng xử trí. `answer(text, detail=True)` in đủ như 🔴
6. ❔ Chưa có dữ liệu — code
7. 🚫 Ngoài phạm vi — code
8. **Đã đối chiếu:** bệnh nền · dị ứng · thuốc đang dùng · thủ thuật · thuốc định kê (tên hiển thị đầy đủ, in một lần). Nhóm trống ghi "không khai". Thuốc trong `unknown_role_drugs` ghi kèm "(không rõ đang dùng hay định kê — đã kiểm cả hai)". Ở tình huống 3, thuốc ghi chung là "Thuốc đã nêu (chưa rõ đang dùng hay định kê)" — không tự gán vai trò *(28/11, B04–B07)*; chỉ in nhóm BS có ghi (bỏ "không khai") và bỏ nhóm thuốc khi câu Q1_DRUG(S) đã nêu tên; không còn nhóm nào thì bỏ cả mục *(28/11)*.
9. **Một câu hỏi mỗi lượt** *(Trung chốt 28/11)*: câu mở đầu tiên theo thứ tự Q5 → Q7 → Q6 → Q8 → Q2 → Q3 (`QUESTION_ORDER`), giữ ca chờ trả lời. Mỗi dòng bot ghép "Bổ sung: …" trả lời câu đang hỏi lúc đó: "không" / "ko" / "không có" / "chưa"… trơn đóng câu đó (Q8: không dùng thuốc; Q5: không gây tê; Q2/Q3: không kê / không làm thêm); Q7 còn đóng khi BS nói giai đoạn ("đang chuẩn bị", "chưa nhổ"…); trả lời có chữ khác chỉ đóng câu khi thông tin mới làm câu đó không còn cần (vd nhắn tên thuốc). Q6 chưa tới lượt hoặc đã đóng thì bệnh nền chưa nhận ra hiện ở ❔. Hết câu hỏi mới nhắc Q4 (không giữ ca). Tình huống 3: Q1
10. Câu chốt — luôn có (trừ tình huống 0 xã giao), code, luôn chứa nguyên văn "BS là người quyết định." (`eval/grade.py` kiểm cụm này)

**Câu cố định** — ⚠️ **bản đề xuất 28/11, chờ Trung duyệt** (bản Trung đã duyệt 27/11 và 28/11 xem lịch sử git của file này). Mục đích: một giọng "em" nhất quán với BS (bỏ "Hệ thống…", "Vui lòng…"), nội dung và giới hạn giữ như bản đã duyệt. Mọi câu vẫn giữ các cụm mà `eval/grade.py` dựa vào (🚫 / "không tư vấn" / "không gợi ý"…, "ẩn danh", "?" hoặc "cho biết", "BS là người quyết định.").

| Mã | Nội dung |
|---|---|
| Q0 | "Anh/chị nhắn em 1 tin gồm (nếu có): bệnh nền, dị ứng, thuốc đang dùng, thủ thuật dự kiến, thuốc định kê nhé. Ví dụ: BN 65t uống Sintrom, ĐTĐ. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen." |
| Q1 | "Anh/chị cho em biết thêm: thuốc nào BN đang dùng, thuốc nào định kê, và định làm thủ thuật gì? Em đối chiếu ngay." |
| Q2 | "Ca này chưa có thuốc định kê. Nếu anh/chị định kê, nhắn thêm tên thuốc để em kiểm tương tác nhé." |
| Q3 | "Ca này chưa có thủ thuật dự kiến. Nếu có, anh/chị nhắn thêm để em kiểm rủi ro thủ thuật nhé." |
| Q4 | "Ca này chưa khai bệnh nền, dị ứng, thuốc đang dùng. Nếu BN có, anh/chị gửi lại cả ca kèm các thông tin đó để em kiểm lại nhé." |
| Q1_DRUG | *(28/11)* "Em nhận ra {tên}. Thuốc này BN đang dùng hay anh/chị định kê, và định làm thủ thuật gì ạ? Nhắn thêm để em đối chiếu nhé." |
| Q1_DRUGS | *(28/11)* "Em nhận ra {tên, tên}. Thuốc nào BN đang dùng, thuốc nào anh/chị định kê, và định làm thủ thuật gì ạ? Nhắn thêm để em đối chiếu nhé." |
| Q5 | "BN có tiền sử dị ứng thuốc tê. Thủ thuật này có dự kiến gây tê không ạ? Nếu có, anh/chị nhắn "có gây tê" để em kiểm." |
| Q6 | "Bệnh nền "{names}" em chưa nhận ra. Anh/chị ghi rõ tên bệnh và tình trạng hiện tại (ổn định hay chưa, đang điều trị gì, chỉ số gần nhất nếu có) để em kiểm." *(thêm 28/11 — cải tiến lượt 2, Trung duyệt 28/11)* |
| Q7 | "Ca đang chuẩn bị hay đang làm thủ thuật, và hiện có chảy máu khó cầm không? Nhắn thêm để em đối chiếu." *(thêm 28/11 — cải tiến lượt 2, Trung duyệt 28/11)* |
| Q8 | "BN có đang dùng thuốc chống đông hoặc kháng tiểu cầu không? Nếu có, nhắn tên thuốc để em kiểm." *(thêm 28/11, Trung chốt)*. Hỏi khi có thủ thuật nhóm `invasive_bleeding` mà chưa khai thuốc đang dùng (kể cả thuốc chưa rõ vai), BS không ghi "không dùng/uống thuốc", và không có rule đã hỏi ý này (`ASKS_ANTICOAG_RULES` = `CR-021`). Giữ ca (`needs_more = True`), không in ✅. Thay cho việc thêm luật riêng cho từng bệnh (stent, van tim, đột quỵ…): BS trả lời tên thuốc thì luật sẵn có (`CR-001`, `CR-004`, `CR-005`…) cảnh báo kèm nguồn. "Khoẻ mạnh" chưa tính là "không dùng thuốc". BS trả lời trơn "không" / "ko" / "không có" / "chưa" khi Q8 là câu đang hỏi cũng tính là không dùng thuốc (một câu mỗi lượt, khối 9). |
| P1 | "⚠️ Tin nhắn có thông tin định danh BN — lần sau anh/chị gửi ca đã ẩn danh giúp em nhé." |
| ❔ thuốc lạ | "❔ Em chưa có dữ liệu cho: {danh sách}, nên không đoán. Nếu là viết tắt hoặc tên chung, anh/chị ghi rõ tên đầy đủ / hoạt chất để em tra lại; nếu không, anh/chị tra thêm Dược thư Quốc gia / tờ hướng dẫn sử dụng nhé." |
| ❔ chưa rõ tên thuốc | *(28/11)* "❔ Chưa rõ tên thuốc: {danh sách}. Em chỉ kiểm được khi có tên thuốc — anh/chị nhờ BN xem vỏ hộp, đơn cũ hoặc sổ khám rồi nhắn thêm tên nhé; chưa có tên thì em chưa kiểm được thuốc này." |
| ❔ bệnh nền / dị ứng / thủ thuật | *(28/11)* "❔ Em chưa có quy tắc cho: {danh sách}, nên chưa kiểm được rủi ro của mục này — phần này anh/chị tự đánh giá nhé." (bản cũ khuyên "ghi rõ … hoạt chất" cả cho "tăng huyết áp") |
| MANY_PATIENTS | *(28/11)* "Tin này có vẻ gồm nhiều BN. Anh/chị gửi mỗi ca một tin giúp em, để em không trộn thuốc của người này sang người kia nhé." |
| JSON_ERROR | "Em đọc tin này chưa trọn — anh/chị kiểm lại mục Đã đối chiếu giúp em." |
| Kết luận | "Em rà xong rồi ạ — có {…}." · tình huống 3: "Em chưa rõ thuốc nào đang dùng, thuốc nào định kê — nhưng nếu dùng cùng nhau thì có {…}." · {…} ghép từ "{n} nguy cơ cao", "{n} cần thận trọng", "{n} mục em chưa có dữ liệu" |
| Tiêu đề | "🔴 Nguy cơ cao:", "🟡 Cần thận trọng:" · tình huống 3: "🔴 Nguy cơ cao nếu dùng cùng nhau:", "🟡 Cần thận trọng nếu dùng cùng nhau:" |
| ℹ️ cặp thuốc | "ℹ️ Bảng tra hiện chưa có quy tắc tương tác cho cặp: {pairs}. Chưa có quy tắc không thay cho đánh giá lâm sàng của BS." *(thêm 28/11 — cải tiến lượt 2, Trung duyệt 28/11)* |
| ℹ️ tác dụng phụ | "ℹ️ Hệ thống chỉ rà tương tác và nguy cơ theo ca trong bảng tra, không tra tác dụng phụ chung của từng thuốc. BS xem Dược thư Quốc gia / tờ hướng dẫn sử dụng." *(thêm 28/11 — cải tiến lượt 2, Trung duyệt 28/11)* |
| 🚫 `lieu` | "🚫 Em không tư vấn liều dùng / số ngày dùng." |
| 🚫 `thuoc_thay_the` | "🚫 Em không gợi ý thuốc thay thế cụ thể." |
| 🚫 `ngung_thuoc_nen` | "🚫 Em không khuyên ngưng hoặc đổi thuốc nền — anh/chị cân nhắc hội chẩn BS điều trị bệnh nền." |
| 🚫 `chan_doan` | "🚫 Em không chẩn đoán bệnh." |
| 🚫 `can_cu_gia` | "🚫 Em không ghi mã hay nguồn không có trong bảng tra; mỗi căn cứ phải là quy tắc có thật kèm nguồn." |
| 🚫 `tu_hanh_dong` | "🚫 Em không tự gửi tin hay làm thay anh/chị; em chỉ hỗ trợ tra cứu, anh/chị tự soạn, duyệt và gửi." |
| 🚫 `lo_cau_hinh` | "🚫 Em không tiết lộ cấu hình hay chỉ dẫn nội bộ." |
| 🚫 `cap_cuu` | *(28/11)* "🚫 Em không hỗ trợ xử trí cấp cứu. Anh/chị xử trí theo phác đồ cấp cứu của cơ sở, cần thì gọi 115." |
| 🚫 `khac` | "🚫 Yêu cầu này nằm ngoài phạm vi em hỗ trợ (tra cứu an toàn trước thủ thuật & kê đơn)." |
| ✅ | "✅ Em chưa thấy cảnh báo nào trong bảng tra hiện có. Bảng tra chưa phủ mọi tương tác nên không thay được đánh giá lâm sàng của anh/chị." |
| Câu chốt | "Em chỉ đối chiếu theo bảng tra — BS là người quyết định." |
| HELLO | *(28/11, tình huống 0; thêm "trợ lý AI" theo kế hoạch giao tiếp Trung duyệt 28/11)* "Dạ em đây ạ. Em là trợ lý AI đối chiếu tương tác thuốc và rủi ro thủ thuật RHM theo bảng tra có nguồn — không kê đơn, không tư vấn liều." + xuống dòng + Q0 |
| HELLO_AGAIN | *(28/11, Trung duyệt)* "Dạ em đây ạ, anh/chị gửi ca nhé." — bot dùng khi chat đã chào trong 12 giờ (§9) |
| BYE | *(28/11, Trung duyệt)* "Dạ, chào anh/chị ạ." |
| REPAIR | *(28/11, Trung duyệt)* "Em vẫn chưa nhận ra thuốc hay thủ thuật nào trong tin này. Anh/chị thử gõ theo mẫu: "BN uống <thuốc đang dùng>. Dự kiến <thủ thuật>. Định kê <thuốc>." Nhắn /huongdan để xem đủ." — bot thay Q1 bằng câu này ở lần thứ 2 liên tiếp không nhận ra thực thể (§9) |
| THANKS | *(28/11, tình huống 0)* "Dạ không có gì ạ. Có ca mới anh/chị cứ nhắn em." |

**Khung một dòng cảnh báo** — hướng xử trí trước, lý do sau; tên ngắn (bỏ chú thích trong ngoặc) *(đổi 28/11)*:

```
Model viết:    [DDI-001] Ibuprofen + Acenocoumarol → {hướng xử trí rút gọn, giữ mọi con số}. (Vì: {cơ chế rút gọn}). Nguồn: {source}
Khung dự phòng: [DDI-001] Ibuprofen + Acenocoumarol → {guidance NGUYÊN VĂN, không cắt câu}. Nguồn: {source}
```

Dòng 🟡 gọn *(28/11, Trung duyệt)*: `[DDI-029] Paracetamol + Warfarin: {câu đầu của mechanism, nguyên văn}. Nguồn: {source}`. Bản "chi tiết" dùng khung như 🔴. **Ngoại lệ** `FULL_MODERATE` (`codebase/agent.py`): rule 🟡 có giá trị nằm ở hành động trong guidance thì vẫn in đủ như 🔴 — hiện chỉ `CR-021` rung nhĩ × thủ thuật chảy máu → hỏi thuốc chống đông *(Trung chốt 28/11)*. Rule MODERATE khác chỉ có hướng xử trí ở bản "chi tiết".

Khung dự phòng (code nối mã HIGH thiếu, dòng model bị loại, hoặc model 2 lỗi) in nguyên văn guidance: bản cũ chỉ lấy câu đầu và làm mất ngưỡng INR của `CR-001`. Khung dự phòng bỏ phần cơ chế cho tin gọn; cơ chế vẫn tra được qua mã và nguồn.

---


*(28/11, issue #31)* Bot Zalo định dạng lại bản tin trước khi gửi (`bot/zalo_bot.py::format_reply`), không đổi chữ của agent nên `run.py eval` không đổi: dòng "Đã đối chiếu — …" tách thành "📋 Em đã đối chiếu:" + gạch đầu dòng, các mục "không khai" gom về "• Chưa khai: …"; trước dòng 🚫 đầu tiên (trừ dòng cấp cứu) thêm "Dạ, phần này nằm ngoài việc em hỗ trợ:"; Q1 khi không nhận ra thực thể nào thêm "Dạ, em chưa đọc ra đủ thông tin để rà ca này." trước và "Hoặc nhắn /moi để bắt đầu ca khác." sau. Không nhận ra cấu trúc hoặc lỗi → gửi nguyên bản gốc.
## 8. Xử lý lỗi

| Lỗi | Xử lý | Ghi trace |
|---|---|---|
| Model lần 1 lỗi API (hết lượt, sai key, mất mạng) | Để exception bay ra (đúng hợp đồng khung BTC; eval ghi vào cột `error`, bot báo "hệ thống đang lỗi") | Khung tự ghi |
| Model lần 1 trả JSON hỏng / thiếu trường | Không gọi lại. Chạy bước 2 với `extracted = None`: chỉ dùng kết quả quét tin gốc (mọi thuốc thành `unknown_role_drugs`). Thêm dòng JSON_ERROR (§7). | `note("json lỗi: …")` |
| Model lần 2 lỗi API, trả rỗng, hoặc dòng không qua kiểm (§5 bước 4) | Code tự viết dòng đó bằng khung dự phòng §7 (guidance nguyên văn) từ dữ liệu CSV. Cảnh báo đã tra được thì vẫn phải đến tay BS | `note("model 2 lỗi, dùng mẫu")` |
| Tin trả lời > 1800 ký tự | Giữ nguyên (không cắt cảnh báo); bot tự chia tin | — |

---

## 9. Bot Zalo: ghép tin bổ sung *(Lĩnh làm sau, khi Nguyên xong phần bot)*

- Bot giữ `pending[chat_id] = (tin đã ghép, thời điểm)` trong RAM.
- Tin mới đến:
  - `/moi` → xoá `pending` của chat đó, trả "Dạ, em đã chuyển sang BN mới. Anh/chị gửi ca tiếp theo nhé." *(28/11, issue #31; trước đó "Đã bắt đầu ca mới.")*
  - Tin xã giao (`agent.small_talk_reply` khác `None`, §6 tình huống 0) → trả câu đó, **không** ghép, **không** đổi `pending` *(28/11: "cảm ơn" từng bị ghép làm bot gửi lại nguyên ca)*.
  - Có `pending` và chưa quá **10 phút** → ghép `tin cũ + "\nBổ sung: " + tin mới`.
  - *(28/11)* Không có `pending` nhưng tin mở đầu bằng "thêm" / "bổ sung" và ca vừa xong (`needs_more = False`) chưa quá 10 phút → ghép với ca vừa xong (`_last_case`). Tin khác là ca mới. `/moi` xoá cả hai.
  - *(28/11, review PR #30)* Tin báo BN khác (`NEW_PATIENT_RE`: "thêm 1 ca …", "thêm BN nữa / khác / mới …", "thêm ca: …") là ca mới, không ghép vào `_pending` lẫn `_last_case`. So trên chữ có dấu nên "thêm cả paracetamol" vẫn là bổ sung; "thêm BN dị ứng …" (không số, không "khác / nữa / mới") cũng vẫn ghép.
  - Ngược lại → dùng tin mới.
- Gọi `answer(text_đã_ghép)`. Kết quả `needs_more = True` → lưu `pending`; `False` → xoá.
- *(28/11)* Ca xong (`needs_more = False`) → cuối tin thêm FOLLOW_UP_HINT: "(Hỏi tiếp cho BN này: nhắn "thêm <tên thuốc / thủ thuật>" trong 10 phút. BN khác: nhắn /moi.)"
- *(28/11)* Ảnh / sticker / tin không có chữ → trả "Em chưa đọc được ảnh, sticker hay tin thoại ạ. Anh/chị gõ tên thuốc, bệnh nền, thủ thuật giúp em — đừng gửi ảnh đơn thuốc thật của BN nhé." Chat chưa kích hoạt thì bỏ qua.
- *(28/11, kế hoạch giao tiếp Trung duyệt — A–F)*
  - **Kích hoạt:** tin ngắn ACTIVATED_TEXT (là trợ lý AI · làm gì · không làm gì · ẩn danh · ví dụ · `/huongdan`); `/huongdan` (và `/help`) in USAGE_TEXT đủ, có danh sách lệnh. Mọi câu của bot xưng "em", gọi "anh/chị".
  - **Chào lại:** loại `greet` (`agent.small_talk_kind`) trong 12 giờ kể từ lần chào trước → HELLO_AGAIN; hỏi "làm được gì" luôn nhận HELLO + Q0. Giờ chào giữ trong RAM.
  - **Hỏi lại tăng dần:** `agent.is_no_entity_reply(output)` đúng 2 lần liên tiếp → thay Q1 bằng REPAIR. Có ca nhận ra thực thể hoặc `/moi` → đếm lại.
  - **`/sai <lý do>`:** ghi log `kind = "feedback"` (đã che số định danh), trả "Dạ em ghi nhận, cảm ơn anh/chị. Nhóm sẽ xem lại cảnh báo này." Không gọi agent, không đổi ca.
  - **"chi tiết":** tin có khối 🟡 → thêm "(Nhắn "chi tiết" trong 10 phút để xem hướng xử trí các mục 🟡.)". "chi tiết" → gọi `answer(ca, detail=True)` với ca đang chờ hoặc ca vừa xong trong 10 phút, không đổi trạng thái ca; không có ca → "Em chưa có ca nào trong 10 phút qua để xem chi tiết ạ. Anh/chị gửi lại ca giúp em nhé." Gọi lại model 1 nên trích thực thể có thể khác lần đầu.
  - **Log:** thêm trường `kind` (`case` · `small_talk` · `feedback` · `detail`). `bot/log_stats.py` chỉ in số đếm, gồm chỉ số gần đúng "để nguyên 🔴" (ca có 🔴 mà 10 phút sau không có ca nào ít dòng 🔴 hơn).
- Tắt bot là mất `pending` (chấp nhận được cho demo). Không ghi `pending` ra đĩa.
- `run.py eval` không đi qua bot nên không bị ảnh hưởng.

---

## 10. Ví dụ đi trọn luồng

Tin: *"BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen"*

| Bước | Kết quả |
|---|---|
| 1 | JSON như §4.2, `out_of_scope = []`, `has_pii = false` |
| 2 | Bệnh nền: `diabetes`, `atrial_fibrillation` (thêm 28/11). Thuốc đang dùng: `acenocoumarol` (vka), `metformin`. Thủ thuật: `invasive_bleeding` + `local_anesthesia` (Trung đã chốt nhổ răng kéo theo gây tê). Thuốc định kê: `amoxicillin`, `ibuprofen` |
| §6 | Có cả thủ thuật và thuốc định kê → tình huống 6, `needs_more = False` |
| 3 | `DDI-001` ibuprofen + vka (HIGH) · `CR-001` vka + thủ thuật chảy máu (HIGH) · `DDI-027` amoxicillin + vka (MODERATE) · `CR-015` ĐTĐ + thủ thuật chảy máu (MODERATE) · `CR-021` rung nhĩ + thủ thuật chảy máu (MODERATE) |
| 4 | Model viết 🔴 (DDI-001, CR-001) và 🟡 (DDI-027, CR-015) |
| Kiểm HIGH | Có đủ `[DDI-001]`, `[CR-001]` → không nối thêm |
| 5 | Kết luận ("có 2 nguy cơ cao, 3 cần thận trọng") → 🔴 → 🟡 (gồm `CR-021` rung nhĩ × thủ thuật chảy máu) → Đã đối chiếu → câu chốt |

Mã quy tắc trên lấy từ CSV v1.1 hiện tại; kết quả thật phụ thuộc bảng alias (vd `dtd type 2` có trong bảng).

---

## 11. Để sau (đã thống nhất, chưa làm ở bản này)

- **3 lớp bảo hiểm thêm bằng code:** regex bắt SĐT/CCCD/mã hồ sơ; danh sách từ khoá vượt quyền gộp với cờ của model; kiểm output không chứa liều (vd `500mg`, `2 viên/ngày`).
- **Nội dung chuyên môn (Trung):** thủ thuật nào kéo theo gây tê; bổ sung bệnh nền hay gặp mà bảng chưa có (rung nhĩ đã thêm 28/11 kèm `CR-021`, nguồn còn UNVERIFIED); bổ sung alias.

---

## 12. Cần xác nhận

| Việc | Ai | Trước |
|---|---|---|
| ~~Một alias nhiều dòng; sửa `validate_csv.py`; tách thuốc phối hợp~~ — đã làm ở PR #5 | Nguyên | — |
| ~~Thủ thuật nào thuộc thêm nhóm `local_anesthesia`~~ — Trung đã chốt, xem bên dưới | Trung | — |
| ~~Câu chữ các câu cố định §7~~ — Trung đã duyệt toàn bộ (gồm Q1 mới, P1, ❔, 5 câu 🚫, ✅) ngày 27/11/2026; Q5 và 3 câu 🚫 `can_cu_gia`, `tu_hanh_dong`, `lo_cau_hinh` ngày 28/11/2026 | Trung | — |
| ~~Cập nhật `team-plan.md` §B~~ — đã làm ở PR #7 | Lĩnh | — |
| Thêm câu thử cho 6 tình huống §6, câu thiếu cả 3 trường đầu (Q4), câu ✅, câu thuốc phối hợp, câu "dị ứng ibuprofen" | Đức | CP3 |
| ~~Cân nhắc metric "output không kết luận an toàn"~~ — metric đã chốt ở PR #6 (5 metric, không có metric này); thiết kế vẫn giữ luật không nói "an toàn" | Đức | — |
| Duyệt câu chữ §7 bản 28/11 (giọng "em", kết luận đầu tin, câu có điều kiện cho tình huống 3) và luật mới: tình huống 3 tra DDI có điều kiện, Q4 không giữ ca | Trung (câu chữ, luật lâm sàng), Lĩnh (code) | Trước khi merge PR |
| 6 rule có "an toàn hơn" trong `clinical_guidance` (DDI-003, DDI-019, DDI-034, CR-007, CR-013, CR-020): khung dự phòng nay in nguyên văn guidance nên cụm này có thể lộ ra tin trả lời (`grade.py` cờ vàng). **Đã đổi chữ 28/11; Trung duyệt câu chữ 28/11/2026, còn chờ Nguyên (data):** DDI-003, DDI-034 → "không làm tăng nguy cơ chảy máu" (cụm của DDI-001); DDI-019 → "không kéo dài QT" (cụm của DDI-013); CR-007, CR-013, CR-020 → "phù hợp" (cụm của CR-019). Sửa cả `ddi_rules.csv` lẫn `build_ddi_and_aliases.py` để build lại không mất | Nguyên (Trung ✓ 28/11) | Trước khi merge PR |
| ~~*(28/11, rà UX)* Duyệt câu chữ mới §7: HELLO, THANKS, Q1_DRUG(S), Q5 ("có gây tê"), 3 câu ❔ tách loại, MANY_PATIENTS, 🚫 `cap_cuu` (có nhắc số 115)~~ — Trung đã duyệt ngày 28/11/2026 | Trung | — |
| *(28/11, rà UX)* Alias đề xuất — **Trung đã duyệt ngày 28/11/2026** (cột `source` ghi "Trung duyệt 28/11/2026"), còn chờ Nguyên (data): `ibu` → ibuprofen, `metro` → metronidazole, `extraction` / `tooth extraction` → nhổ răng, `chich ap xe` / `trich ap xe` / `dan luu ap xe` → rạch dẫn lưu áp xe, `dieu tri tuy` / `lay tuy` / `dieu tri noi nha` → nhóm không xâm lấn (như `chua tuy`) | Nguyên (Trung ✓ 28/11) | Trước khi merge PR |
| *(28/11, rà UX)* Chưa nhận ra, **cần quyết định lâm sàng + nguồn** (bot hiện báo ❔ "chưa có quy tắc"): "tăng huyết áp" đã kiểm soát / chưa rõ (chỉ có dạng "chưa kiểm soát" — ca P5), "lấy cao răng" trơn (trên hay dưới nướu?), van tim cơ học, đặt stent < 6 tháng, xạ trị vùng đầu cổ, đang cho con bú, hen, dị ứng sulfa, dị ứng cao su, ghép xương, nâng xoang | Trung (luật), Nguyên (data) | Sau CP4 |
| *(28/11, rà UX)* Thuốc không rõ tên theo nhóm ("thuốc chống đông", "thuốc loãng xương chích hằng năm"): có nên thêm thực thể "nhóm, chưa rõ tên" kèm câu hỏi riêng (VKA / DOAC / kháng tiểu cầu? chích hay uống?) và cảnh báo chung không | Trung | Sau CP4 |
| ~~*(28/11, rà UX)* Bản tin gọn cho điện thoại~~ — làm cho 🟡 theo kế hoạch giao tiếp Trung duyệt 28/11 (🔴 giữ nguyên). `eval --try 27` (không tính là lượt) cho `eval/grade.py` xếp từng câu đúng như run-2 (9 🟢 / 18 🟡 / 0 🔴); **chưa chấm tay**. Trung chốt 28/11: `CR-021` in đủ (`FULL_MODERATE`); các rule MODERATE khác giữ dạng gọn | Trung | Xong 28/11 |
| *(28/11)* **Nói về bot khi thuyết trình** (kế hoạch giao tiếp, mục G): chỉ nói bot giúp BS phát hiện sớm tương tác thuốc và rủi ro thủ thuật, có nguồn, BS quyết định. Không nói bot cải thiện kết cục BN hay giảm biến chứng — nhóm chưa có số liệu đó (Penda Health, 39.849 lượt khám, cũng chưa chứng minh được kết cục). Số được dẫn: kết quả eval (run-2 26/27) và số đếm từ `bot/log_stats.py` | Người làm slide | CP4 |

**Trung chốt ngày 27/11/2026:** Q0–Q4 giữ nguyên văn bản của Lĩnh. Tự gán thêm nhóm `local_anesthesia` cho nhổ răng, cấy implant và phẫu thuật nha chu/tạo vạt *(28/11/2026 Trung chốt thêm: rạch/chích/trích/dẫn lưu áp xe; chữa/điều trị/lấy tủy, nội nha — không gồm trám, khám, lấy cao trên nướu)*. Với các thủ thuật còn lại, chỉ gán nhóm này khi tin nhắn ghi rõ có gây tê. Bảng alias đã có các nhóm bổ sung. CLI CP2 hiện chỉ tra DDI; bước tra rủi ro theo nhóm thủ thuật thuộc luồng triển khai của Lĩnh.

**Lĩnh cập nhật sau đó (27/11), đối chiếu `eval/benchmark.csv` 17 câu:**
- **Q1** đổi thành câu hỏi rõ thuốc nào đang dùng, thuốc nào định kê, thủ thuật gì — để khớp kỳ vọng "hỏi lại vai trò / tên thuốc" của B02, B04–B07, B15.
- Tin không có thực thể nào (tình huống 1, §6) trả **Q1** thay cho Q0 — khớp B02. Q0 chỉ còn dùng cho `/start`, `/help` của bot.
- Câu **❔** thêm phần mời ghi rõ tên đầy đủ / hoạt chất khi là viết tắt hoặc tên chung — khớp B12 ("th áp"), B14 ("thuốc điều trị duy trì").
- **Rủi ro đã biết:** Trung đã bổ sung phần xác minh giai đoạn thủ thuật và chảy máu khó cầm vào `clinical_guidance` của `CR-016` (27/11/2026) cho `B11`; còn lại `B13` (nhắc đánh giá sớm vì ca cấp) là kỳ vọng lâm sàng ngoài bảng tra nên có thể trượt do thiết kế không cho model tự thêm kiến thức.

**Khác `team-plan.md` §B:**
1. Thêm nhánh ✅ "Không phát hiện cảnh báo" (không gọi model 2).
2. Model 1 còn 2 cờ (`out_of_scope`, `has_pii`); "thiếu thông tin" do code xác định theo §6. 4 câu Q1–Q4 thay cho "hỏi lại 1 câu".
3. Cờ `out_of_scope` không dừng luồng.
4. Thêm bước 5 ráp tin bằng code; model 2 chỉ viết khối 🔴 🟡.
5. `answer()` trả thêm `needs_more`; bot ghép tin bổ sung.
6. Một alias nhiều dòng; khớp dài nhất không chồng lấn.
7. Model 2 lỗi → code dùng mẫu thay vì báo lỗi.
8. *(28/11)* Tình huống 3 tra DDI có điều kiện; kết luận đầu tin; khung dòng cảnh báo hướng xử trí trước; khung dự phòng giữ nguyên văn guidance; kiểm số trong dòng model; Q4 không bật `needs_more`.
