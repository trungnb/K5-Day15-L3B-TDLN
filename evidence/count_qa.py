"""Đếm mẫu hỏi đáp RHM công khai — evidence/qa_sample.csv → số cho evidence/data-mining.md.

Chạy:  python evidence/count_qa.py            (mặc định đọc evidence/qa_sample.csv)
       python evidence/count_qa.py <file.csv>

Chỉ dùng thư viện chuẩn. Người khác chạy lại trên cùng file phải ra cùng số.

Cột của qa_sample.csv (mỗi dòng = 1 câu hỏi công khai, lấy LIÊN TIẾP mới nhất, không lọc trước):
  id               Q01, Q02… theo thứ tự thu thập
  nguon            tên trang (vd medlatec, edoctor)
  url              link công khai của câu hỏi
  ngay_dang        YYYY-MM-DD — ngày câu hỏi được đăng (để trống nếu trang không ghi)
  ngay_xem         YYYY-MM-DD — ngày nhóm mở trang
  trich_dan        tối đa 2 câu, ĐÃ BỎ tên người hỏi / chi tiết định danh
  lien_quan        co | khong — câu hỏi có nhắc bệnh nền / thuốc đang dùng / dị ứng thuốc
                   GẮN VỚI thủ thuật RHM hoặc thuốc dùng trong RHM không
  yeu_to           các giá trị cách nhau bằng "|": benh_nen | thuoc_nen | di_ung | mang_thai_cho_bu | khong
  thu_thuat_thuoc  các giá trị cách nhau bằng "|": nho_rang | tieu_phau | implant | cao_rang | tiem_te |
                   khang_sinh | giam_dau | corticoid | khac | khong
  nguoi_gan_nhan   ai gán nhãn (vd Nguyen, Duc) — Đức rà lại
  ghi_chu          tự do
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

COLS = ["id", "nguon", "url", "ngay_dang", "ngay_xem", "trich_dan", "lien_quan",
        "yeu_to", "thu_thuat_thuoc", "nguoi_gan_nhan", "ghi_chu"]
LIEN_QUAN = {"co", "khong"}
YEU_TO = {"benh_nen", "thuoc_nen", "di_ung", "mang_thai_cho_bu", "khong"}
THU_THUAT_THUOC = {"nho_rang", "tieu_phau", "implant", "cao_rang", "tiem_te",
                   "khang_sinh", "giam_dau", "corticoid", "khac", "khong"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def split(v):
    return [x.strip() for x in (v or "").split("|") if x.strip()]


def check(rows):
    errs = []
    seen = set()
    for i, r in enumerate(rows, start=2):  # dòng 1 là tiêu đề
        rid = r["id"].strip()
        if not rid:
            errs.append("dòng %d: thiếu id" % i)
        elif rid in seen:
            errs.append("dòng %d: id %s bị trùng" % (i, rid))
        seen.add(rid)
        if not r["url"].strip().startswith("http"):
            errs.append("dòng %d (%s): thiếu url" % (i, rid))
        if not DATE.match(r["ngay_xem"].strip()):
            errs.append("dòng %d (%s): ngay_xem phải dạng YYYY-MM-DD" % (i, rid))
        if r["ngay_dang"].strip() and not DATE.match(r["ngay_dang"].strip()):
            errs.append("dòng %d (%s): ngay_dang phải dạng YYYY-MM-DD hoặc để trống" % (i, rid))
        if not r["trich_dan"].strip():
            errs.append("dòng %d (%s): thiếu trich_dan" % (i, rid))
        if r["lien_quan"].strip() not in LIEN_QUAN:
            errs.append("dòng %d (%s): lien_quan phải là co|khong" % (i, rid))
        for col, allowed in (("yeu_to", YEU_TO), ("thu_thuat_thuoc", THU_THUAT_THUOC)):
            vals = split(r[col])
            bad = [v for v in vals if v not in allowed]
            if bad:
                errs.append("dòng %d (%s): %s có giá trị lạ %s" % (i, rid, col, bad))
            if r["lien_quan"].strip() == "co" and (not vals or vals == ["khong"]):
                errs.append("dòng %d (%s): lien_quan=co nhưng %s trống/khong" % (i, rid, col))
    return errs


def pct(x, n):
    return "%d/%d (%.0f%%)" % (x, n, 100.0 * x / n) if n else "%d/0" % x


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("qa_sample.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLS if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit("Thiếu cột: %s" % ", ".join(missing))
        rows = list(reader)

    n = len(rows)
    print("File: %s" % path)
    print("Mẫu số N = %d câu hỏi%s" % (n, "" if n >= 40 else "  ⚠️ cần N ≥ 40"))
    errs = check(rows)
    if errs:
        print("\nLỗi dữ liệu (%d) — sửa trước khi lấy số:" % len(errs))
        for e in errs:
            print("  - " + e)
        sys.exit(1)
    if not n:
        return

    lq = [r for r in rows if r["lien_quan"].strip() == "co"]
    print("\n| Đếm gì | x / N | Ghi chú |")
    print("|---|---|---|")
    print("| Câu hỏi nhắc bệnh nền/thuốc nền/dị ứng gắn với thủ thuật hoặc thuốc RHM | %s | lien_quan=co |" % pct(len(lq), n))
    yt = Counter(v for r in lq for v in split(r["yeu_to"]))
    for k in sorted(YEU_TO - {"khong"}):
        print("| — yếu tố: %s | %s | trên N; 1 câu có thể nhiều yếu tố |" % (k, pct(yt[k], n)))
    tt = Counter(v for r in lq for v in split(r["thu_thuat_thuoc"]))
    for k in sorted(THU_THUAT_THUOC - {"khong"}):
        if tt[k]:
            print("| — gắn với: %s | %s | trên N |" % (k, pct(tt[k], n)))

    nguon = Counter(r["nguon"].strip() for r in rows)
    ngay = sorted(r["ngay_dang"].strip() for r in rows if r["ngay_dang"].strip())
    print("\nNguồn: " + ", ".join("%s=%d" % kv for kv in nguon.most_common()))
    if ngay:
        print("Khoảng ngày đăng: %s → %s" % (ngay[0], ngay[-1]))
    print("Ngày xem: " + ", ".join(sorted({r["ngay_xem"].strip() for r in rows})))


if __name__ == "__main__":
    main()
