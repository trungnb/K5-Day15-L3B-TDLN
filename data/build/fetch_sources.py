"""Tải tài liệu & dữ liệu công khai chính thống vào data/raw/ (đã gitignore) và ghi MANIFEST.json.

Chỉ dùng thư viện chuẩn Python. Chạy từ thư mục gốc repo:
    python3 data/build/fetch_sources.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
USER_AGENT = "TDLN-RHM-Hackathon-Fetcher/1.0 (https://github.com)"
TIMEOUT_SEC = 30

DDINTER_ATC_LETTERS = ("A", "B", "C", "D", "G", "H", "J", "L", "M", "N", "P", "R", "S", "V")
DDINTER_PAGES = (
    "https://ddinter.scbdd.com/download/",
    "http://ddinter.scbdd.com/download/",
    "https://ddinter2.scbdd.com/download/",
)
QD5948_PDF_URL = (
    "http://bvphuchoichucnangvinhphuc.vn/SiteFolders/benhvienphuchoi/403/"
    "5948.qd-byt_%20DM%20tuong%20tac%20thuoc%20chong%20chi%20dinh.pdf"
)
QD3108_PDF_URL = (
    "https://chanthuongvacotsong.bachmai.gov.vn/wp-content/uploads/2026/01/"
    "BE1BAA3n-cuE1BB91i-20150728-HD-CC490C490T-RHM.pdf"
)
SDCEP_ANTICOAG_QRG_PDF = (
    "https://www.sdcep.org.uk/media/33nfexkn/"
    "sdcep-anticoagulants-quick-reference-guide-2nd-edition.pdf"
)
AAOMS_MRONJ_EPMC_JSON = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
    "query=EXT_ID:35300956%20AND%20SRC:MED&resultType=core&format=json"
)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self._current_href = v.strip()
                self._text_parts = []
                break

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = " ".join("".join(self._text_parts).split())
            self.links.append((self._current_href, text))
            self._current_href = None
            self._text_parts = []


def _fetch_bytes(url: str, *, method: str = "GET", timeout: int = TIMEOUT_SEC) -> tuple[int, dict[str, str], bytes]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = int(getattr(resp, "status", 200))
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = b"" if method == "HEAD" else resp.read()
        return status, headers, body


def _safe_filename(url: str, fallback: str) -> str:
    path_part = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    name = Path(path_part).name.strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or fallback


def _extract_links(html_bytes: bytes, base_url: str, exts: tuple[str, ...]) -> list[tuple[str, str]]:
    text = html_bytes.decode("utf-8", errors="replace")
    parser = _LinkParser()
    parser.feed(text)
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for href, label in parser.links:
        abs_url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        low_path = urllib.parse.unquote(parsed.path).lower()
        if any(low_path.endswith(ext) for ext in exts) and abs_url not in seen:
            seen.add(abs_url)
            results.append((abs_url, label))
    return results


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_bytes(body: bytes, expected_kind: str, content_type: str = "") -> tuple[str, str | None]:
    if expected_kind == "pdf":
        if not body.startswith(b"%PDF-"):
            return "invalid_pdf", f"Response does not start with %PDF- (content-type={content_type})"
        return "pdf", None
    if expected_kind == "csv":
        head = body[:512].decode("utf-8-sig", errors="replace").lstrip()
        low_head = head.lower()
        first_line = head.splitlines()[0] if head.splitlines() else ""
        if low_head.startswith("<!doctype") or low_head.startswith("<html") or "," not in first_line:
            return "invalid_csv", f"Not a valid CSV header: {first_line[:80]!r}"
        line_count = max(0, len(body.splitlines()) - 1)
        return f"csv:{line_count}_rows", None
    if expected_kind == "xml":
        head = body[:512].decode("utf-8", errors="replace").lstrip()
        low_head = head.lower()
        if not head.startswith("<") or low_head.startswith("<!doctype") or low_head.startswith("<html"):
            return "invalid_xml", f"Not valid XML: {head[:80]!r}"
        return "xml", None
    if expected_kind == "json":
        try:
            json.loads(body.decode("utf-8"))
        except Exception as exc:
            return "invalid_json", f"Not valid JSON: {type(exc).__name__}: {exc}"
        return "json", None
    return expected_kind, None


def _validate_and_save(
    entry_id: str,
    url: str,
    dest_path: Path,
    expected_kind: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if dest_path.exists() and not force:
        existing = dest_path.read_bytes()
        rows_or_type, err = _validate_bytes(existing, expected_kind)
        if err is None:
            return {
                "id": entry_id,
                "url": url,
                "path": str(dest_path.relative_to(ROOT)),
                "status": "cached",
                "bytes": len(existing),
                "sha256": _sha256_hex(existing),
                "rows_or_type": rows_or_type,
                "error": None,
            }

    try:
        status, headers, body = _fetch_bytes(url)
    except urllib.error.HTTPError as exc:
        return {
            "id": entry_id,
            "url": url,
            "path": None,
            "status": exc.code,
            "bytes": 0,
            "sha256": None,
            "rows_or_type": expected_kind,
            "error": f"HTTPError: {exc.code} {exc.reason}",
        }
    except Exception as exc:
        return {
            "id": entry_id,
            "url": url,
            "path": None,
            "status": None,
            "bytes": 0,
            "sha256": None,
            "rows_or_type": expected_kind,
            "error": f"{type(exc).__name__}: {exc}",
        }

    rows_or_type, err = _validate_bytes(body, expected_kind, headers.get("content-type", ""))
    if err is not None:
        return {
            "id": entry_id,
            "url": url,
            "path": None,
            "status": status,
            "bytes": len(body),
            "sha256": None,
            "rows_or_type": rows_or_type,
            "error": err,
        }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(body)
    rel_path = str(dest_path.relative_to(ROOT))
    return {
        "id": entry_id,
        "url": url,
        "path": rel_path,
        "status": status,
        "bytes": len(body),
        "sha256": _sha256_hex(body),
        "rows_or_type": rows_or_type,
        "error": None,
    }


def _fetch_ddinter(entries: list[dict[str, Any]], *, force: bool = False) -> None:
    dd_dir = RAW_DIR / "ddinter"
    if not force:
        cached_csvs = sorted(dd_dir.glob("ddinter_downloads_code_*.csv"))
        if cached_csvs:
            all_valid = True
            cached_entries: list[dict[str, Any]] = []
            for path in cached_csvs:
                fname = path.name
                url = f"https://ddinter.scbdd.com/static/media/download/{fname}"
                entry = _validate_and_save(f"ddinter:{fname}", url, path, "csv", force=False)
                if entry["error"] is not None:
                    all_valid = False
                    break
                cached_entries.append(entry)
            if all_valid:
                print(f"[info] DDInter: dùng lại {len(cached_entries)} file CSV đã kiểm hợp lệ (dùng --force để tải lại)")
                entries.extend(cached_entries)
                return

    discovered_csvs: list[str] = []
    for page_url in DDINTER_PAGES:
        try:
            _, _, body = _fetch_bytes(page_url, timeout=15)
            found = [u for u, _ in _extract_links(body, page_url, (".csv",))]
            if found:
                discovered_csvs = found
                print(f"[info] DDInter download page OK ({page_url}): {len(found)} CSV links")
                break
        except Exception as exc:
            print(f"[info] DDInter page check ({page_url}): {type(exc).__name__}: {exc}")

    if discovered_csvs:
        for csv_url in discovered_csvs:
            fname = _safe_filename(csv_url, "ddinter.csv")
            entry = _validate_and_save(f"ddinter:{fname}", csv_url, dd_dir / fname, "csv", force=force)
            entries.append(entry)
        return

    # Fallback: thử trực tiếp theo chữ cái ATC (https trước, chỉ thử http nếu https lỗi)
    for letter in DDINTER_ATC_LETTERS:
        fname = f"ddinter_downloads_code_{letter}.csv"
        urls = [
            f"https://ddinter.scbdd.com/static/media/download/{fname}",
            f"http://ddinter.scbdd.com/static/media/download/{fname}",
        ]
        last_entry: dict[str, Any] | None = None
        for url in urls:
            entry = _validate_and_save(f"ddinter:ATC_{letter}", url, dd_dir / fname, "csv", force=force)
            last_entry = entry
            if entry["error"] is None:
                break
        if last_entry is not None:
            entries.append(last_entry)


def _fetch_moh_vn(entries: list[dict[str, Any]], *, force: bool = False) -> None:
    moh_dir = RAW_DIR / "moh_vn"
    # 1. QĐ 5948/QĐ-BYT (Danh mục tương tác thuốc chống chỉ định)
    entries.append(
        _validate_and_save(
            "moh:qd5948_2021_pdf",
            QD5948_PDF_URL,
            moh_dir / "qd5948_2021_danh_muc_tuong_tac_thuoc_chong_chi_dinh.pdf",
            "pdf",
            force=force,
        )
    )
    # 2. QĐ 3108/QĐ-BYT (Hướng dẫn chẩn đoán & điều trị một số bệnh về RHM - BV Bạch Mai)
    entries.append(
        _validate_and_save(
            "moh:qd3108_2015_pdf",
            QD3108_PDF_URL,
            moh_dir / "qd3108_2015_hd_chan_doan_dieu_tri_rhm.pdf",
            "pdf",
            force=force,
        )
    )


def _fetch_guidelines(entries: list[dict[str, Any]], *, force: bool = False) -> None:
    guide_dir = RAW_DIR / "guidelines"

    # 1. SDCEP Anticoagulants & Antiplatelets Quick Reference Guide (2nd Ed., 2022)
    entries.append(
        _validate_and_save(
            "guideline:sdcep_anticoag_qrg_2022",
            SDCEP_ANTICOAG_QRG_PDF,
            guide_dir / "sdcep-anticoagulants-quick-reference-guide-2nd-edition.pdf",
            "pdf",
            force=force,
        )
    )

    # 2. AAOMS MRONJ 2022 Position Paper (Europe PMC PMID 35300956 JSON; DOI 10.1016/j.joms.2022.02.008)
    entries.append(
        _validate_and_save(
            "guideline:aaoms_mronj_2022_pmid35300956",
            AAOMS_MRONJ_EPMC_JSON,
            guide_dir / "aaoms_mronj_2022_pmid35300956.json",
            "json",
            force=force,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Tải dữ liệu & guideline công khai vào data/raw/")
    parser.add_argument("--force", action="store_true", help="Tải lại toàn bộ kể cả file đã tồn tại")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    _fetch_ddinter(entries, force=args.force)
    _fetch_moh_vn(entries, force=args.force)
    _fetch_guidelines(entries, force=args.force)

    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    manifest_path = RAW_DIR / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok_count = sum(1 for e in entries if e["error"] is None and e["path"] is not None)
    err_count = sum(1 for e in entries if e["error"] is not None)
    print(f"\n=== Tổng kết tải tài liệu ({manifest_path.relative_to(ROOT)}) ===")
    print(f"Đã tải hợp lệ: {ok_count} file · Lỗi/bỏ qua: {err_count}\n")
    for e in entries:
        status_str = str(e["status"]) if e["status"] is not None else "ERR"
        if e["path"]:
            print(f"[OK]  {e['id']:<34} {status_str:>4}  {e['bytes']:>9} B  {e['rows_or_type']:<18}  {e['path']}")
        elif e["error"] is None:
            print(f"[CHK] {e['id']:<34} {status_str:>4}  {e['rows_or_type']}")
        else:
            print(f"[ERR] {e['id']:<34} {status_str:>4}  {e['error']}")


if __name__ == "__main__":
    main()
