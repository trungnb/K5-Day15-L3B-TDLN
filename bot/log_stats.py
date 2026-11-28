"""Đếm số liệu từ log bot (bot/logs/*.jsonl) — chỉ in số đếm, không in nội dung tin.

Chạy từ gốc repo (trên VM):  bot/.venv/bin/python bot/log_stats.py bot/logs
Chỉ đọc log, không ghi gì. Log ghi trước 28/11 không có trường "kind": loại tin được suy từ input/output.

"Để nguyên 🔴" là chỉ số gần đúng (kiểu Penda Health "left in red"): một ca có khối 🔴, rồi trong 10 phút
cùng chat không có ca nào sau đó có ít dòng 🔴 hơn. Log không ghi mã rule nên đếm dòng 🔴 từ chữ trong output.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys

BOT_DIR = Path(__file__).resolve().parent
CODEBASE_DIR = BOT_DIR.parent / "codebase"
sys.path = [p for p in sys.path if Path(p or ".").resolve() != BOT_DIR]
if str(CODEBASE_DIR) not in sys.path:
    sys.path.insert(0, str(CODEBASE_DIR))

from agent import OUT_OF_SCOPE, TEXT as AGENT_TEXT  # noqa: E402

FEEDBACK_ACK = "Dạ em ghi nhận, cảm ơn anh/chị. Nhóm sẽ xem lại cảnh báo này."   # giữ khớp bot/zalo_bot.py
WINDOW_SEC = 600
SMALL_TALK_OUTPUTS = (AGENT_TEXT["THANKS"], AGENT_TEXT["BYE"], AGENT_TEXT["HELLO_AGAIN"])


def _kind(rec: dict) -> str:
    if rec.get("kind"):
        return str(rec["kind"])
    inp, out = str(rec.get("input") or ""), str(rec.get("output") or "")
    if inp.strip().lower().startswith("/sai"):
        return "feedback"
    if out.startswith(AGENT_TEXT["HELLO"]) or out in SMALL_TALK_OUTPUTS:
        return "small_talk"
    return "case"


def _block_lines(output: str, mark: str) -> int:
    """Số dòng "- …" ngay dưới các tiêu đề bắt đầu bằng `mark` (🔴 / 🟡)."""
    count, inside = 0, False
    for line in (output or "").splitlines():
        if line.startswith(mark):
            inside = True
        elif inside and line.startswith("- "):
            count += 1
        else:
            inside = False
    return count


def _ts(rec: dict) -> float | None:
    try:
        return datetime.fromisoformat(str(rec.get("ts"))).timestamp()
    except ValueError:
        return None


def compute(records: list[dict]) -> dict:
    by_kind: Counter = Counter()
    refusals: Counter = Counter()
    stats = {"turns": 0, "cases_with_high": 0, "cases_with_moderate": 0, "follow_up_them": 0,
             "repair": 0, "errors": 0, "red_cases": 0, "left_in_red": 0}
    cases_by_chat: dict[str, list[tuple[float, int]]] = {}
    invite_chats: set[str] = set()
    stats["invite_activated"] = 0
    for rec in records:
        kind = _kind(rec)
        by_kind[kind] += 1
        if kind == "invite":   # chat chưa có quyền: không phải lượt BS dùng bot
            invite_chats.add(str(rec.get("chat")))
            stats["invite_activated"] += str(rec.get("input") or "").endswith(" activated")
            continue
        stats["turns"] += 1
        out = str(rec.get("output") or "")
        if rec.get("error"):
            stats["errors"] += 1
        if kind != "case":
            continue
        reds = _block_lines(out, "🔴")
        stats["cases_with_high"] += reds > 0
        stats["cases_with_moderate"] += _block_lines(out, "🟡") > 0
        stats["repair"] += AGENT_TEXT["REPAIR"] in out
        stats["follow_up_them"] += str(rec.get("input") or "").strip().lower().startswith(("thêm", "them"))
        for code, text in OUT_OF_SCOPE.items():
            if text in out:
                refusals[code] += 1
        ts = _ts(rec)
        if ts is not None:
            cases_by_chat.setdefault(str(rec.get("chat")), []).append((ts, reds))
    for cases in cases_by_chat.values():
        cases.sort()
        for i, (ts, reds) in enumerate(cases):
            if reds == 0:
                continue
            stats["red_cases"] += 1
            fixed = any(later_reds < reds for later_ts, later_reds in cases[i + 1:] if later_ts - ts <= WINDOW_SEC)
            stats["left_in_red"] += not fixed
    stats["by_kind"] = dict(by_kind)
    stats["invite_chats"] = len(invite_chats)
    stats["refusals"] = dict(refusals)
    return stats


def load(log_dir: Path) -> tuple[list[dict], int]:
    records, bad = [], 0
    for path in sorted(log_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if isinstance(rec, dict):
                records.append(rec)
            else:
                bad += 1
    return records, bad


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    log_dir = Path(args[0]) if args else BOT_DIR / "logs"
    if not log_dir.is_dir():
        print(f"Không thấy thư mục log: {log_dir}")
        return 1
    records, bad = load(log_dir)
    stats = compute(records)
    stats["bad_lines"] = bad
    print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
