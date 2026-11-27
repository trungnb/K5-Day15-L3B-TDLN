"""Gom mẫu hỏi đáp RHM công khai từ AloBacsi → evidence/qa_sample.csv (cột nhãn để trống).

Nguồn: mục "Khám bệnh online" của AloBacsi, 2 chuyên mục nha:
    https://alobacsi.com/kham-benh-online/nha-khoa
    https://alobacsi.com/kham-benh-online/rang-ham-mat
robots.txt của alobacsi.com cho phép (chỉ chặn /tim-kiem, /api/, /admin/). Chỉ đọc trang công khai,
không đăng nhập, nghỉ 1 giây giữa các lần tải.

Cách lấy mẫu (evidence/data-mining.md §1): với MỖI chuyên mục lấy toàn bộ trang 1 = 25 câu mới nhất
LIÊN TIẾP, KHÔNG lọc theo nội dung; gộp 2 chuyên mục, bỏ câu trùng. Chỉ lấy trang 1 vì phân trang
của AloBacsi chạy bằng JavaScript (?page=2 trả lại nội dung trang 1, kiểm ngày 27/11/2026) — nếu gộp rồi
cắt N câu mới nhất chung thì sẽ hổng các câu cũ hơn của chuyên mục ra bài nhanh hơn.

Chạy:  python evidence/crawl_qa.py            (ghi đè evidence/qa_sample.csv)
       python evidence/crawl_qa.py --out <file.csv>

Riêng tư: KHÔNG lưu tên người hỏi (trường author). trich_dan = tối đa 2 câu đầu của câu hỏi,
đã che SĐT/email; người gán nhãn vẫn phải đọc lại và bỏ chi tiết định danh còn sót.
Chỉ dùng thư viện chuẩn.
"""
import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import re
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://alobacsi.com/kham-benh-online"
CATEGORIES = ["nha-khoa", "rang-ham-mat"]
UA = "Mozilla/5.0 (compatible; hackathon-research-script; +https://github.com)"
CACHE = Path(tempfile.gettempdir()) / "tdln_qa_cache"
COLS = ["id", "nguon", "url", "ngay_dang", "ngay_xem", "trich_dan", "lien_quan",
        "yeu_to", "thu_thuat_thuoc", "nguoi_gan_nhan", "ghi_chu"]


def fetch(url):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if f.exists():
        return f.read_text(encoding="utf-8")
    time.sleep(1)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print("  bỏ qua %s (HTTP %d)" % (url, e.code))
        return ""
    f.write_text(text, encoding="utf-8")
    return text


def list_urls(cat, pages):
    urls = []
    for p in range(1, pages + 1):
        page_url = "%s/%s" % (BASE, cat) if p == 1 else "%s_%s?page=%d" % (BASE, cat, p)
        h = fetch(page_url)
        for u in re.findall(r'href="(%s/[a-z0-9-]+\.html)"' % re.escape(BASE), h):
            if u not in urls:
                urls.append(u)
    return urls


def parse(url):
    h = fetch(url)
    q = None
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try:
            d = json.loads(m.group(1), strict=False)
        except ValueError:
            continue
        if d.get("@type") == "Question":
            q = d
            break
    m = re.search(r"Ngày đăng:\s*(?:\d{1,2}:\d{2}\s*)?(\d{2})/(\d{2})/(\d{4})", h)
    ngay = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else ""
    if not q:
        return None
    return {"url": url, "ngay_dang": ngay,
            "tieu_de": html.unescape(q.get("name", "")).strip(),
            "cau_hoi": html.unescape(q.get("text", "")).strip()}


def scrub(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*Ảnh bạn đọc gửi AloBacsi\s*", " ", text)
    text = re.sub(r"\s*\([^()]{2,60}\)\s*$", "", text.strip())  # chữ ký "(Tên, Tỉnh)" cuối câu hỏi
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text)
    text = re.sub(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)", "[sđt]", text)
    return text.strip()


def first_sentences(text, k=2, limit=300):
    parts = re.split(r"(?<=[.!?…])\s+", scrub(text))
    out = " ".join(parts[:k]).strip()
    return out if len(out) <= limit else out[:limit].rsplit(" ", 1)[0] + " …"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("qa_sample.csv")))
    ap.add_argument("--force", action="store_true", help="ghi đè cả khi file đã có nhãn")
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists() and not a.force:
        with open(out, encoding="utf-8-sig", newline="") as f:
            if any(r.get("lien_quan", "").strip() for r in csv.DictReader(f)):
                raise SystemExit("%s đã có nhãn — không ghi đè. Dùng --out <file khác> hoặc --force." % out)

    cats = {}  # url -> danh sách chuyên mục chứa nó
    for c in CATEGORIES:
        us = list_urls(c, 1)
        print("Chuyên mục %s: %d câu ở trang 1" % (c, len(us)))
        for u in us:
            cats.setdefault(u, []).append(c)
    urls = list(cats)
    items = [x for x in (parse(u) for u in urls) if x and x["ngay_dang"]]
    for x in items:
        x["chuyen_muc"] = "+".join(cats[x["url"]])
    items.sort(key=lambda x: (x["ngay_dang"], x["url"]), reverse=True)
    sample = items

    today = dt.date.today().isoformat()
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for i, x in enumerate(sample, 1):
            q = x["cau_hoi"] or x["tieu_de"]
            w.writerow({"id": "Q%02d" % i, "nguon": "alobacsi", "url": x["url"],
                        "ngay_dang": x["ngay_dang"], "ngay_xem": today,
                        "trich_dan": first_sentences(q), "lien_quan": "", "yeu_to": "",
                        "thu_thuat_thuoc": "", "nguoi_gan_nhan": "",
                        "ghi_chu": "chuyên mục: %s; tiêu đề: %s" % (x["chuyen_muc"], scrub(x["tieu_de"]))})
    print("Gộp, bỏ trùng: %d câu (%d có ngày đăng) → ghi %d câu vào %s" % (len(urls), len(items), len(sample), a.out))
    if sample:
        print("Khoảng ngày đăng của mẫu: %s → %s" % (sample[-1]["ngay_dang"], sample[0]["ngay_dang"]))


if __name__ == "__main__":
    main()
