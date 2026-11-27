# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp.

## Dataset 1 · Bảng tương tác thuốc RHM (`data/ddi_rules.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `check_drug_interactions()` (Bước 3 — tra tất định cặp thuốc nền × thuốc định kê RHM). |
| Từ đâu | **1.** **QĐ 5948/QĐ-BYT (30/12/2021)** — *Danh mục tương tác thuốc chống chỉ định* (Bộ Y tế VN, bản PDF 176 trang).<br>**2.** **DDInter** (`https://ddinter.scbdd.com/download/`, 8 file CSV nhóm ATC: A, B, D, H, L, P, R, V; tổng 222.383 dòng gốc; license **CC BY-NC-SA 4.0** — chỉ dùng học thuật/hackathon). |
| Xử lý những bước gì | Tải về `data/raw/` (đã gitignore, checksum SHA-256 trong `data/raw/MANIFEST.json`) bằng `data/build/fetch_sources.py` → lọc cặp liên quan thuốc định kê RHM & assert khớp trực tiếp từng cặp/mức độ (`Major`→`HIGH`, `Moderate`→`MODERATE`) bằng `data/build/build_ddi_and_aliases.py` → kiểm toàn vẹn & an toàn ngôn từ bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **32 rule** (`HIGH = 23`, `MODERATE = 9`). |
| Phiên bản / ngày lấy | QĐ 5948/QĐ-BYT (2021) & DDInter tải ngày **27/11/2026**. |
| Nhãn | Thật (tổng hợp từ nguồn chính thống/học thuật; diễn giải cơ chế & hướng xử trí tiếng Việt có gắn cờ `[BS Trung duyệt]` cho các cặp DDInter). |
| Giới hạn | **1.** 8 file DDInter gốc chỉ có 5 cột (`Drug_A`, `Drug_B`, `Level`), không có cột cơ chế/xử trí nên phần diễn giải do nhóm tổng hợp và BS RHM duyệt lại.<br>**2.** `Acenocoumarol` (Sintrom) có `0` dòng `Major` trong DDInter nên nhóm dùng quy tắc nhóm `class:vka` (áp chung với `Warfarin`, đồng bộ phân nhóm VKA trong QĐ 5948 tr. 169).<br>**3.** `Dabigatran` thiếu trong 8 file DDInter đã tải → bù bằng quy tắc nhóm `class:doac`. |

## Dataset 2 · Bảng rủi ro lâm sàng & thủ thuật RHM (`data/clinical_risk_rules.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `check_clinical_risks()` (Bước 3 — tra rủi ro bệnh nền / dị ứng / thuốc nền × thủ thuật RHM hoặc thuốc định kê). |
| Từ đâu | **1.** **SDCEP (2022)** — *Management of Dental Patients Taking Anticoagulants or Antiplatelet Drugs, Quick Reference Guide (2nd Ed.)*.<br>**2.** **AAOMS (2022)** — *Position Paper on MRONJ—2022 Update* (*JOMS* 80(5):920–943, PMID `35300956`, metadata xác minh qua Europe PMC).<br>**3.** **QĐ 3108/QĐ-BYT (2015)** (208 trang) & **Dược thư Quốc gia VN lần 3 (2022)** *(mục `CR-008`..`CR-016` đang gắn cờ `[cần BS Trung kiểm trang]` do không có bản PDF Dược thư trong `data/raw/`)*. |
| Xử lý những bước gì | Trích lọc quy tắc có nguồn từng dòng → kiểm schema, enums, chống trùng tổ hợp và kiểm an toàn (cấm gợi ý liều / cấm khuyên tự ngưng thuốc nền) bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **16 rule** (`CR-001`..`CR-016`). |
| Phiên bản / ngày lấy | SDCEP QRG (03/2022) & AAOMS (05/2022) tải ngày **27/11/2026**. |
| Nhãn | Thật (trích hướng dẫn lâm sàng; các dòng gắn `[cần BS Trung kiểm trang]` chờ BS RHM duyệt trước CP3). |
| Giới hạn | Mới phủ 16 kịch bản rủi ro phổ biến nhất tại ghế răng ngoại trú (chống đông, MRONJ, dị ứng, loét dạ dày, CKD, thai kỳ, THA chưa kiểm soát, ĐTĐ, rối loạn đông máu); chưa phủ toàn bộ bệnh hiếm hoặc chỉ định nhi khoa. |

## Dataset 3 · Từ điển chuẩn hoá thực thể (`data/entity_aliases.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `normalize_entities()` (Bước 2 — đổi tên biệt dược VN, viết tắt lâm sàng sang `canonical_id` và `drug_class`). |
| Từ đâu | Tên hoạt chất gốc lấy từ DDInter & QĐ 5948/QĐ-BYT (kèm `DDInterID` trong cột `notes`); tên biệt dược VN & viết tắt thường gặp do BS RHM trong nhóm tổng hợp (chờ bổ sung thêm từ câu trả lời phỏng vấn `P1–P3`). |
| Xử lý những bước gì | Sinh tự động bằng `data/build/build_ddi_and_aliases.py` và kiểm trùng lặp / khoá ngoại 100% với 2 bảng rule bằng `data/build/validate_csv.py`. |
| Số dòng / số đoạn | **166 alias** phủ **55 thực thể chuẩn** (thuốc định kê RHM, thuốc nền, dị ứng, bệnh nền, nhóm thủ thuật). |
| Phiên bản / ngày lấy | v1 — ngày **27/11/2026**. |
| Nhãn | Thật (ánh xạ tên thuốc/thuật ngữ chuẩn; không chứa dữ liệu bệnh nhân). |
| Giới hạn | Chưa phủ toàn bộ biệt dược thương mại trên thị trường VN; tên thuốc ngoài bảng sẽ được đánh dấu `unmapped` và báo *"Chưa có dữ liệu"* thay vì đoán. |
