# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp.

## Dataset 1 · Bảng tương tác thuốc RHM (`data/ddi_rules.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `check_drug_interactions()` (Bước 3 — tra tất định cặp thuốc nền × thuốc định kê RHM). |
| Từ đâu | **1.** **QĐ 5948/QĐ-BYT (30/12/2021)** — *Danh mục tương tác thuốc chống chỉ định* (Bộ Y tế VN, bản PDF 176 trang).<br>**2.** **DDInter** (`https://ddinter.scbdd.com/download/`, 8 file CSV nhóm ATC: A, B, D, H, L, P, R, V; tổng 222.383 dòng gốc; license **CC BY-NC-SA 4.0** — chỉ dùng học thuật/hackathon).<br>**3.** **FDA Prescribing Information / CredibleMeds / Drugs.com** (đối chiếu bổ sung cho `DDI-013` và `DDI-019` — kéo dài khoảng QT với Amiodarone). |
| Xử lý những bước gì | Tải về `data/raw/` (đã gitignore, checksum SHA-256 trong `data/raw/MANIFEST.json`) bằng `data/build/fetch_sources.py` → lọc cặp liên quan thuốc định kê RHM & assert khớp trực tiếp từng cặp/mức độ (`Major`→`HIGH`, `Moderate`→`MODERATE`) bằng `data/build/build_ddi_and_aliases.py` → kiểm toàn vẹn & an toàn ngôn từ bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **36 rule** (`HIGH = 23`, `MODERATE = 13`). |
| Phiên bản / ngày lấy | QĐ 5948/QĐ-BYT (2021) & DDInter tải ngày **27/11/2026**. |
| Nhãn | Thật (tổng hợp từ nguồn chính thống/học thuật; đã đối chiếu trực tiếp file gốc và được BS RHM trong nhóm (Nguyễn Bảo Trung) duyệt lâm sàng ngày 27/11/2026). |
| Giới hạn | **1.** 8 file DDInter gốc chỉ có 5 cột (`Drug_A`, `Drug_B`, `Level`), không có cột cơ chế/xử trí nên phần diễn giải do nhóm tổng hợp và BS RHM duyệt lại.<br>**2.** `Acenocoumarol` (Sintrom) có `0` dòng `Major` trong DDInter nên nhóm dùng quy tắc nhóm `class:vka` (áp chung với `Warfarin`, đồng bộ phân nhóm VKA trong QĐ 5948 tr. 169).<br>**3.** `Dabigatran` thiếu trong 8 file DDInter đã tải → bù bằng quy tắc nhóm `class:doac`. |

## Dataset 2 · Bảng rủi ro lâm sàng & thủ thuật RHM (`data/clinical_risk_rules.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `check_clinical_risks()` (Bước 3 — tra rủi ro bệnh nền / dị ứng / thuốc nền × thủ thuật RHM hoặc thuốc định kê). |
| Từ đâu | **1.** **SDCEP (2022)** — *Management of Dental Patients Taking Anticoagulants or Antiplatelet Drugs, Quick Reference Guide (2nd Ed.)*.<br>**2.** **AAOMS (2022)** — *Position Paper on MRONJ—2022 Update* (*JOMS* 80(5):920–943, PMID `35300956`, metadata xác minh qua Europe PMC).<br>**3.** **Dược thư Quốc gia VN lần 3 (QĐ 3445/QĐ-BYT, 23/12/2022)** (*Amoxicilin, Ibuprofen, Celecoxib, Lidocain, Epinephrin*), **QĐ 472/QĐ-BYT (29/02/2024)** (*Hemophilia*), **WFH Guidelines 3rd Ed. (2020)** & **ADA Oral Health Topics: Diabetes / ADA Standards of Care**. |
| Xử lý những bước gì | Trích lọc quy tắc có nguồn từng dòng → kiểm schema, enums, chống trùng tổ hợp và kiểm an toàn (cấm gợi ý liều / cấm khuyên tự ngưng thuốc nền) bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **21 rule** (`CR-001`..`CR-021`, gồm cả nhóm COX-2 `celecoxib`). |
| Phiên bản / ngày lấy | SDCEP QRG (03/2022) & AAOMS (05/2022) tải ngày **27/11/2026**; QĐ 472/QĐ-BYT (29/02/2024). |
| Nhãn | Thật (trích hướng dẫn lâm sàng). BS RHM trong nhóm Nguyễn Bảo Trung chọn sử dụng bản sửa hiện tại của `CR-002` và `CR-005` ngày 27/11/2026. Hai dòng đã được đối chiếu với SDCEP QRG, trang 3 và 5. `CR-021` (rung nhĩ × thủ thuật chảy máu, MODERATE, chỉ nhắc hỏi thuốc chống đông) là đề xuất của nhóm: **UNVERIFIED** — chưa có tài liệu nguồn trích dẫn (SDCEP QRG, QĐ 5948, QĐ 3108 trong `data/raw/` không nhắc rung nhĩ); Nguyễn Bảo Trung chọn dùng ngày 28/11/2026 để rung nhĩ không bị báo ✅ khi BN chưa khai thuốc chống đông. Cần bổ sung nguồn trước khi coi là quy tắc có căn cứ. |
| Giới hạn | Mới phủ 21 kịch bản rủi ro phổ biến nhất tại ghế răng ngoại trú (chống đông, MRONJ, dị ứng, loét dạ dày, CKD, thai kỳ cho cả NSAID và COX-2, THA chưa kiểm soát, ĐTĐ, rối loạn đông máu); chưa phủ toàn bộ bệnh hiếm hoặc chỉ định nhi khoa. Bản PDF toàn văn của *Dược thư QG VN 2022* và *AAOMS 2022* không lưu trong `data/raw/` (chỉ đối chiếu chuyên luận/metadata); `QĐ 3108/QĐ-BYT (2015)` (208 trang) đã được kiểm trực tiếp nhưng chỉ gồm 57 bệnh lý RHM, không phủ bệnh nền toàn thân nên không dùng làm nguồn cho bảng này. |

## Dataset 3 · Từ điển chuẩn hoá thực thể (`data/entity_aliases.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `normalize_entities()` (Bước 2 — đổi tên biệt dược VN, viết tắt lâm sàng sang `canonical_id` và `drug_class`). |
| Từ đâu | Tên hoạt chất gốc lấy từ DDInter & QĐ 5948/QĐ-BYT (kèm `DDInterID` trong cột `notes`); tên biệt dược lưu hành tại Việt Nam đối chiếu qua Nhà thuốc Long Châu, Trung Tâm Thuốc, Thuốc Biệt Dược, Nha Khoa Mall & Vinmec cùng viết tắt lâm sàng RHM (chờ bổ sung thêm từ phỏng vấn `P1–P3`). |
| Xử lý những bước gì | Sinh tự động bằng `data/build/build_ddi_and_aliases.py` (gắn cờ `combo:` trong cột `notes` với thuốc đa thành phần) và kiểm trùng lặp / khoá ngoại 100% với 2 bảng rule bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **253 dòng alias** phủ **60 thực thể chuẩn** (thuốc định kê RHM, thuốc tê có/không co mạch, thuốc nền, dị ứng, bệnh nền, nhóm thủ thuật). Nhổ răng, cấy implant và phẫu thuật nha chu/tạo vạt có thêm dòng `local_anesthesia`. |
| Phiên bản / ngày lấy | v1.1 — ngày **27/11/2026**; 28/11/2026 thêm `nho r18`, `nho r28` và bệnh nền `rung nhi` (`atrial_fibrillation`); 28/11/2026 (rà UX, Trung duyệt 28/11/2026, cột `source` ghi rõ) thêm viết tắt / cách gọi khác của thực thể đã có: `ibu`, `metro`, `extraction`, `tooth extraction`, `chich ap xe`, `trich ap xe`, `dan luu ap xe`, `dieu tri tuy`, `lay tuy`, `dieu tri noi nha`. |
| Nhãn | Thật (ánh xạ tên thuốc/thuật ngữ chuẩn; không chứa dữ liệu bệnh nhân). Nguyễn Bảo Trung chọn sử dụng bản sửa hiện tại của `alaxan`, `rach ap xe` và `lay cao duoi nuou` ngày 27/11/2026. Mã thành phần Alaxan đã đối chiếu với `DDI-029`; hai alias thủ thuật đã đối chiếu với SDCEP QRG, trang 3. |
| Giới hạn | Chưa phủ toàn bộ biệt dược thương mại trên thị trường VN; tên thuốc ngoài bảng sẽ được đánh dấu `unmapped` và báo *"Chưa có dữ liệu"* thay vì đoán. Mỗi thành phần có mã chuẩn được lưu thành một dòng cho biệt dược phối hợp. `notes` giữ khai báo thành phần để validator đối chiếu. Spiramycin, esomeprazole và hydrochlorothiazide chưa có thực thể chuẩn trong bản này. |
