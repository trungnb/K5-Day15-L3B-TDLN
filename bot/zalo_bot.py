"""Lớp vỏ mỏng cho Zalo Bot (long polling) — chỉ nhận tin, gọi agent.answer(text) và trả lời.

Không chứa logic y khoa hay tra cứu; `run.py`, `eval/run_eval.py`, `cost/simulate.py` không import file này.
Chạy từ thư mục gốc repo:
    bot/.venv/bin/python bot/zalo_bot.py

Hướng dẫn tạo bot mới và vận hành chi tiết: xem `docs/zalo-bot.md`.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import functools
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
from typing import Any

BOT_DIR = Path(__file__).resolve().parent
ROOT = BOT_DIR.parent
CODEBASE_DIR = ROOT / "codebase"
# Tránh bot/zalo_bot.py tự che khuất thư viện `zalo_bot` khi chạy trực tiếp `python bot/zalo_bot.py`.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != BOT_DIR]
if str(CODEBASE_DIR) not in sys.path:
    sys.path.insert(0, str(CODEBASE_DIR))

import followups  # noqa: E402
import tracing  # noqa: E402


class _ThreadCase:
    """Thay `tracing._case` (khung, không sửa file) bằng bản riêng cho từng luồng: mỗi ca chạy trọn
    begin→end trong một luồng của asyncio.to_thread, nên nhiều ca song song không ghi lẫn trace."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _d(self) -> dict:
        d = getattr(self._local, "d", None)
        if d is None:
            d = self._local.d = {"id": None, "events": None, "t0": 0.0}
        return d

    def __getitem__(self, key: str) -> Any:
        return self._d()[key]

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._d().update(*args, **kwargs)


tracing._case = _ThreadCase()
from agent import TEXT as AGENT_TEXT, answer, small_talk_kind, small_talk_text  # noqa: E402  (agent -> ai.py nạp .env)
from reply import Reply, render_chat, render_detail  # noqa: E402

from zalo_bot import Update  # noqa: E402
from zalo_bot.constants import ChatAction  # noqa: E402
from zalo_bot.ext import (  # noqa: E402
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

CHUNK = 1900  # giữ dưới ngưỡng 2000 ký tự/tin nhắn của Zalo sendMessage
LOG_DIR = ROOT / "bot" / "logs"
ALLOWED_CHATS_FILE = ROOT / "bot" / "allowed_chats.json"

MAX_INVITE_FAILS = 5
INVITE_WINDOW_SEC = 600

# Ghép tin bổ sung (docs/design.md §9): giữ ca đang chờ bổ sung trong RAM, không ghi ra đĩa.
PENDING_TTL_SEC = 600
SEND_ATTEMPTS = 3        # gửi lỗi thì thử lại (issue #32 A); mốc đề xuất, không có nguồn
SEND_RETRY_SEC = 1.0
ERROR_TEXT = "Dạ em xin lỗi, hệ thống tra cứu đang lỗi — anh/chị thử lại sau ít phút giúp em nhé."
MAX_PENDING_CHARS = 4000
NEW_CASE_TEXT = "Dạ, em đã chuyển sang BN mới. Anh/chị gửi ca tiếp theo nhé."
FOLLOW_UP_HINT = "(Hỏi tiếp cho BN này: nhắn \"thêm <tên thuốc / thủ thuật>\" trong 10 phút. BN khác: nhắn /moi.)"
NON_TEXT_TEXT = ("Em chưa đọc được ảnh, sticker hay tin thoại ạ. Anh/chị gõ tên thuốc, bệnh nền, thủ thuật giúp em — "
                 "đừng gửi ảnh đơn thuốc thật của BN nhé.")
FOLLOW_UP_RE = re.compile(r"^\s*(?:thêm|them|bổ sung|bo sung)\b", re.IGNORECASE)
# "Thêm 1 ca: …", "Thêm BN nữa …", "Thêm ca: …" là BN khác → ca mới, không ghép (review PR #30, Nguyên).
# So trên chữ có dấu: "thêm cả paracetamol" vẫn là bổ sung; "thêm BN dị ứng …" (không số / không "khác, nữa, mới") cũng vậy.
NEW_PATIENT_RE = re.compile(
    r"^\s*(?:thêm|them|bổ sung|bo sung)\s+(?:"
    r"(?:\d+|một|mot)\s+(?:ca|bn|bệnh nhân|benh nhan)\b"
    r"|(?:ca|bn|bệnh nhân|benh nhan)\s+(?:khác|khac|nữa|nua|mới|moi)\b"
    r"|ca\s*:)", re.IGNORECASE)
MERGED_NOTE = "(Em đã ghép với tin trước của ca này. Nếu là BN khác, nhắn /moi rồi gửi lại.)"
# Ca đang chờ mà tin mới tả BN khác (followups.new_patient; log VM 28/11 15:35) → ca mới, báo cách ghép nếu cùng BN.
SPLIT_NOTE = "(Tin này tả BN khác nên em đối chiếu như ca mới. Nếu vẫn là BN trước, nhắn \"thêm\" kèm nội dung.)"
# Tin đã ghép thì MERGED_NOTE đã nhắc /moi — gợi ý hỏi tiếp bỏ phần /moi cho tin đỡ dài (review PR #30, Nguyên ý 5).
FOLLOW_UP_HINT_MERGED = "(Hỏi tiếp cho BN này: nhắn \"thêm <tên thuốc / thủ thuật>\" trong 10 phút.)"
# Kế hoạch giao tiếp Trung duyệt 28/11 (docs/design.md §7, §9).
GREET_AGAIN_SEC = 12 * 3600   # chào lại trong 12 giờ → câu ngắn HELLO_AGAIN (mốc đề xuất, không có nguồn)
DETAIL_RE = re.compile(r"^\s*(?:xem\s+|cho\s+(?:em\s+|mình\s+|minh\s+)?xem\s+)?chi\s+ti[eếê]t"
                       r"(?:\s+(?:đi|di|nhé|nhe|nha|ạ|a))?\s*[.!?]*\s*$", re.IGNORECASE)
NO_DETAIL_TEXT = "Em chưa có ca nào trong 10 phút qua để xem chi tiết ạ. Anh/chị gửi lại ca giúp em nhé."
FEEDBACK_ACK = "Dạ em ghi nhận, cảm ơn anh/chị. Nhóm sẽ xem lại cảnh báo này."
DROPPED_NOTE = (
    f"⏱️ Ca trước đã quá {PENDING_TTL_SEC // 60} phút (hoặc quá dài) nên em KHÔNG ghép, tin này được đối chiếu như ca mới. "
    "Nếu là cùng BN, anh/chị gửi lại một tin đủ bệnh nền, thuốc đang dùng, thủ thuật và thuốc định kê."
)

# Lọc số định danh bằng code trước khi gọi model và ghi log (design §11). Chỉ bắt SĐT và dãy 9–12 chữ số
# (CMND/CCCD/mã hồ sơ); số lâm sàng như INR 2.5, HbA1c 7.2%, 81mg, R48 không bị đụng tới.
_PHONE_RE = re.compile(r"(?<![\w.,])(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\w|[.,]\d)")
_LONG_ID_RE = re.compile(r"(?<![\w.,])\d{9,12}(?!\w|[.,]\d)")
ID_MASK = "[số định danh đã ẩn]"

TOKEN = os.environ.get("ZALO_BOT_TOKEN", "").strip()
INVITE_CODE = (os.environ.get("ZALO_INVITE_CODE") or "").strip()
ENV_ALLOWED_CHAT_IDS = {
    part.strip()
    for part in (os.environ.get("ZALO_ALLOWED_CHAT_IDS") or "").split(",")
    if part.strip()
}

# Số ca chạy agent cùng lúc (mỗi ca 1–3 lần gọi model): chỉnh theo hạn mức RPM của model. Chưa đo tải thật.
AGENT_CONCURRENCY = max(1, int(os.environ.get("BOT_AGENT_CONCURRENCY") or "8"))
_agent_slots = asyncio.Semaphore(AGENT_CONCURRENCY)
_chat_locks: dict[str, asyncio.Lock] = {}   # tin cùng một chat xử lý lần lượt (giữ thứ tự ghép ca)
_chat_users: dict[str, int] = {}            # số task đang giữ hoặc chờ khoá của chat; về 0 mới xoá khoá
_inflight: set[asyncio.Task] = set()        # giữ tham chiếu task đang chạy để không bị GC
_allowlist_lock = asyncio.Lock()
_prompted_chats: set[str] = set()
_failed_attempts: dict[str, list[float]] = {}


# ------------------------------------------------------------------ trạng thái hội thoại (RAM, mất khi restart)

@dataclass
class CaseState:
    """Ca gần nhất của một chat: chữ đã gửi agent, bản tin agent trả, lúc trả, và ca có đang chờ bổ sung không."""
    text: str
    reply: Reply
    at: float
    waiting: bool   # needs_more: tin sau tự ghép vào ca; False = ca vừa xong, chỉ ghép khi BS mở đầu bằng "thêm"


@dataclass
class Conversation:
    """Mọi trạng thái bot giữ cho một chat (design §9) — một chỗ, một lần dọn (/moi)."""
    case: CaseState | None = None
    misses: int = 0                 # số lần liên tiếp không nhận ra thực thể nào
    greeted_at: float | None = None

    def recent(self, now: float) -> CaseState | None:
        """Ca còn trong PENDING_TTL_SEC (để ghép tin, xem "chi tiết")."""
        return self.case if self.case and now - self.case.at <= PENDING_TTL_SEC else None

    def compose(self, text: str, now: float) -> tuple[str, str]:
        """Chữ gửi agent cho tin mới, và trạng thái: "new" không ghép · "merged" đã ghép vào ca ·
        "split" ca đang chờ nhưng tin tả BN khác (followups.new_patient) nên không ghép ·
        "dropped" có ca để ghép nhưng quá hạn / quá dài nên bỏ — phải báo BS, vì tin bổ sung đứng một mình
        có thể thiếu thuốc nền và mất cảnh báo HIGH (vd warfarin rồi "Định kê ibuprofen")."""
        case = self.case
        if NEW_PATIENT_RE.match(text or "") or case is None or not (case.waiting or FOLLOW_UP_RE.match(text or "")):
            return text, "new"
        if not FOLLOW_UP_RE.match(text or "") and followups.new_patient(case.reply.checked, text):
            self.case = None
            return text, "split"
        merged = followups.merge(case.text, text)
        if now - case.at > PENDING_TTL_SEC or len(merged) > MAX_PENDING_CHARS:
            self.case = None
            return text, "dropped"
        return merged, "merged"

    def remember(self, text: str, reply: Reply, now: float) -> None:
        self.case = CaseState(text, reply, now, waiting=reply.needs_more)

    def count_miss(self, reply: Reply) -> bool:
        """Đếm lần liên tiếp không nhận ra thực thể nào; True từ lần thứ 2 (đưa câu mẫu REPAIR, design §9)."""
        self.misses = self.misses + 1 if reply.is_no_entity else 0
        return self.misses >= 2

    def greet(self, now: float) -> bool:
        """Ghi lần chào; True nếu đã chào trong GREET_AGAIN_SEC (đáp câu ngắn)."""
        again = self.greeted_at is not None and now - self.greeted_at <= GREET_AGAIN_SEC
        self.greeted_at = now
        return again

    def new_case(self) -> None:
        self.case, self.misses = None, 0


_conversations: dict[str, Conversation] = {}


def _conv(chat_id: str) -> Conversation:
    return _conversations.setdefault(chat_id, Conversation())

_DOCTOR_PREFIX_RE = re.compile(
    r"^(?:(?:bs|dr)(?:\.|\s|$)|(?:bác|bac)\s*s[ĩi](?:\s|$))",
    re.IGNORECASE,
)

USAGE_TEXT = (
    "Em là trợ lý AI tra cứu an toàn trước thủ thuật & kê đơn RHM (bản thử hackathon).\n\n"
    "Cách dùng: nhắn 1 tin gồm đủ 5 ý (nếu có): bệnh nền, dị ứng, thuốc đang dùng, "
    "thủ thuật dự kiến và thuốc định kê.\n\n"
    "Lưu ý bắt buộc:\n"
    "• Chỉ dùng ca giả lập hoặc đã ẩn danh — KHÔNG gửi họ tên, SĐT, mã hồ sơ hay ảnh đơn thuốc thật của BN.\n"
    "• Em chỉ hỗ trợ đối chiếu cảnh báo kèm nguồn; không kê đơn, không tư vấn liều, BS là người quyết định.\n"
    "• Thiếu ý nào em sẽ hỏi lại; anh/chị nhắn bổ sung trong 10 phút là em ghép vào ca đang hỏi.\n\n"
    "Lệnh:\n"
    "• /moi — chuyển sang BN khác.\n"
    "• \"thêm <thuốc / thủ thuật>\" — hỏi tiếp cho ca vừa xong (trong 10 phút).\n"
    "• \"chi tiết\" — xem lý do, hướng xử trí 🟡 và nguồn của ca vừa xong.\n"
    "• /sai <lý do> — báo cảnh báo sai hoặc không hữu ích.\n\n"
    "Ví dụ:\n"
    "BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen"
)
START_TEXT = f"Dạ chào anh/chị ạ! {USAGE_TEXT}"
ACTIVATED_TEXT = (
    "Đã kích hoạt. Chào {title} ạ!\n"
    "Em là trợ lý AI tra cứu an toàn trước thủ thuật & kê đơn RHM (bản thử hackathon).\n"
    "• Em làm: đối chiếu tương tác thuốc và rủi ro thủ thuật theo bảng tra có nguồn.\n"
    "• Em không làm: kê đơn, tư vấn liều, xử trí cấp cứu. BS là người quyết định.\n"
    "• Chỉ gửi ca đã ẩn danh — không họ tên, SĐT, mã hồ sơ, ảnh đơn thật.\n"
    "Ví dụ: BN 65t uống Sintrom, ĐTĐ. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen.\n"
    "Nhắn /huongdan để xem đủ cách dùng."
)


def _load_saved_chat_ids(path: Path = ALLOWED_CHATS_FILE) -> set[str]:
    if not path.exists():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"[warn] không đọc được {path.name}: {redact(f'{type(exc).__name__}: {exc}')}")
        return set()

    items = raw.get("chat_ids") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        print(f"[warn] định dạng {path.name} không hợp lệ, bỏ qua danh sách đã lưu.")
        return set()
    return {
        str(item).strip()
        for item in items
        if (isinstance(item, str) or (isinstance(item, int) and not isinstance(item, bool)))
        and str(item).strip()
    }


def _save_chat_ids(chat_ids: set[str], path: Path = ALLOWED_CHATS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"chat_ids": sorted(chat_ids)}, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=".allowed_chats.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


SAVED_CHAT_IDS = _load_saved_chat_ids()
ALLOWED_CHAT_IDS = set(ENV_ALLOWED_CHAT_IDS) | set(SAVED_CHAT_IDS)


def split_message(text: str, limit: int = CHUNK) -> list[str]:
    text = (text or "").strip() or "(trống)"
    chunks: list[str] = []
    while len(text) > limit:
        cut = max(
            text.rfind("\n\n", 0, limit),
            text.rfind("\n", 0, limit),
            text.rfind(" ", 0, limit),
        )
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    chunks.append(text)
    return chunks


def redact(text: str, token: str = TOKEN) -> str:
    if token and len(token) >= 8:
        text = text.replace(token, "[REDACTED]")
    return re.sub(r"bot\d{6,}:[A-Za-z0-9_-]{10,}", "bot[REDACTED]", text)


# Che định danh trước khi ghi log (không áp vào tin gửi BS). Regex không bắt được tên BN viết tự do,
# nên khi agent đã gắn cờ định danh (câu P1 trong output) thì bỏ hẳn tin gốc khỏi log.
PII_WARNING = AGENT_TEXT["P1"]
PII_DROPPED = "[đã bỏ: tin có thông tin định danh]"
PII_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r"(?i)((?:mã|số)\s*(?:hồ\s*sơ|bệnh\s*nhân|bn|bhyt)(?:\s*(?:bn|bệnh\s*nhân))?|mhs|pid)\s*[:#]?\s*[a-z0-9][a-z0-9-]*"),
     r"\1 [mã]"),
    (re.compile(r"\b[A-Za-z]{2}\d{13}\b"), "[mã BHYT]"),
    (re.compile(r"(?<!\d)\+?\d(?:[\s.-]?\d){8,11}(?!\d)"), "[số]"),  # SĐT, CCCD/CMND: 9–12 chữ số
)


def mask_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _chat_hash(chat_id: str) -> str:
    return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:10]


def log_turn(
    *,
    chat_id: str,
    user_input: str,
    output: str,
    summary: dict[str, Any],
    error: str = "",
    drop_input: bool = False,
    kind: str = "case",
) -> None:
    """kind: "case" · "small_talk" · "feedback" (/sai) · "detail" ("chi tiết") · "non_text" (ảnh/sticker)
    · "new_case" (/moi) · "invite" (chat chưa có quyền, chỉ ghi bước) — bot/log_stats.py đếm theo trường này."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    log_path = LOG_DIR / f"{now.strftime('%Y%m%d')}.jsonl"
    models = summary.get("models") or []
    record = {
        "ts": now.isoformat(),
        "chat": _chat_hash(chat_id),
        "kind": kind,
        "input": PII_DROPPED if drop_input else mask_pii(user_input),
        "output": mask_pii(output),
        "pii_dropped": drop_input,
        "model": ", ".join(models) if models else "",
        "tokens_in": int(summary.get("tokens_in") or 0),
        "tokens_out": int(summary.get("tokens_out") or 0),
        "error": mask_pii(error),
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def mask_identifiers(text: str) -> tuple[str, bool]:
    """Thay SĐT và dãy số giấy tờ bằng ID_MASK. Trả (chữ đã lọc, có thay gì không)."""
    masked = _LONG_ID_RE.sub(ID_MASK, _PHONE_RE.sub(ID_MASK, text or ""))
    return masked, masked != (text or "")


def run_agent(text: str) -> tuple[Reply, dict[str, Any]]:
    tracing.begin("zalo")
    try:
        reply = answer(text)["reply"]
    finally:
        summary, _ = tracing.end()
    return reply, summary


def compose_reply(reply: Reply, *, repeat_miss: bool, case_status: str, had_ids: bool) -> str:
    """Tin gửi BS cho một ca: bản tin agent (dạng chat) + các câu của lớp hội thoại, đúng thứ tự đọc:
    ⏱️ ca quá hạn và ⚠️ định danh lên đầu (BS phải thấy trước dòng ✅), gợi ý hỏi tiếp / ghi chú đã ghép xuống cuối."""
    text = render_chat(reply, repeat_miss=repeat_miss)
    if not reply.needs_more and not reply.head_only:   # chỉ dòng cấp cứu: không có ca để hỏi tiếp
        text += "\n" + (FOLLOW_UP_HINT_MERGED if case_status == "merged" else FOLLOW_UP_HINT)
    if had_ids and not text.startswith(PII_WARNING):
        text = f"{PII_WARNING}\n{text}"
    if case_status == "merged":
        text += "\n" + MERGED_NOTE
    elif case_status == "dropped":
        text = f"{DROPPED_NOTE}\n{text}"
    elif case_status == "split":
        text += "\n" + SPLIT_NOTE
    return text


def _extract_chat_id(update: Update) -> str | None:
    msg = update.message
    if msg is None or msg.chat is None:
        return None
    if msg.from_user and msg.from_user.is_bot:
        return None
    return str(msg.chat.id) if msg.chat.id is not None else None


def _extract_display_name(update: Update) -> str:
    candidates: list[Any] = []
    eff_user = getattr(update, "effective_user", None)
    if eff_user is not None:
        candidates.append(eff_user)
    msg = getattr(update, "message", None)
    from_user = getattr(msg, "from_user", None) if msg is not None else None
    if from_user is not None and from_user is not eff_user:
        candidates.append(from_user)

    for user in candidates:
        for attr in ("display_name", "full_name", "first_name", "name"):
            val = getattr(user, attr, None)
            if isinstance(val, str):
                cleaned = " ".join(val.split())[:60].strip()
                if cleaned:
                    return cleaned
    return ""


def _format_doctor_title(display_name: str) -> str:
    cleaned = " ".join((display_name or "").split())[:60].strip()
    if not cleaned:
        return "BS"
    if _DOCTOR_PREFIX_RE.match(cleaned):
        return cleaned
    return f"BS {cleaned}"


def _invite_prompt_text(update: Update) -> str:
    title = _format_doctor_title(_extract_display_name(update))
    return (
        f"Chào {title} ạ, anh/chị nhập mã mời giúp em để bắt đầu dùng "
        "trợ lý AI tra cứu an toàn RHM (chỉ cần nhập 1 lần)."
    )


def _parse_command(text: str) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return "", ""
    parts = stripped.split(None, 1)
    cmd = parts[0].split("@", 1)[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def _verify_invite_code(candidate: str, expected: str | None = None) -> bool:
    target = (INVITE_CODE if expected is None else expected).strip().upper()
    guess = (candidate or "").strip().upper()
    if not target or not guess:
        return False
    return hmac.compare_digest(guess.encode("utf-8"), target.encode("utf-8"))


def _prune_attempts(chat_id: str, now: float) -> list[float]:
    cutoff = now - INVITE_WINDOW_SEC
    recent = [ts for ts in _failed_attempts.get(chat_id, []) if ts > cutoff]
    if recent:
        _failed_attempts[chat_id] = recent
    else:
        _failed_attempts.pop(chat_id, None)
    return recent


def _is_invite_throttled(chat_id: str, now: float | None = None) -> bool:
    ts = time.monotonic() if now is None else now
    return len(_prune_attempts(chat_id, ts)) >= MAX_INVITE_FAILS


def _record_invite_failure(chat_id: str, now: float | None = None) -> None:
    ts = time.monotonic() if now is None else now
    recent = _prune_attempts(chat_id, ts)
    recent.append(ts)
    _failed_attempts[chat_id] = recent


async def _grant_access(chat_id: str) -> None:
    async with _allowlist_lock:
        SAVED_CHAT_IDS.add(chat_id)
        ALLOWED_CHAT_IDS.add(chat_id)
        _failed_attempts.pop(chat_id, None)
        _prompted_chats.discard(chat_id)
        try:
            _save_chat_ids(SAVED_CHAT_IDS, ALLOWED_CHATS_FILE)
        except OSError as exc:
            print(f"[warn] không lưu được allowed_chats.json: {redact(f'{type(exc).__name__}: {exc}')}")


def _is_non_private_chat(update: Update) -> bool:
    msg = getattr(update, "message", None)
    chat = getattr(msg, "chat", None) if msg is not None else None
    if chat is None:
        return False
    chat_type = getattr(chat, "type", None) or getattr(chat, "chat_type", None)
    if chat_type is None:
        return False
    raw_type = getattr(chat_type, "value", chat_type)
    return str(raw_type).strip().lower() != "private"


def _log_invite(chat_id: str, step: str) -> None:
    """Người chưa có quyền: chỉ ghi bước (prompt · wrong · activated · …), không ghi chữ đã gõ, tên hay mã mời —
    để đếm được bao nhiêu người mới vào chat mà chưa dùng được bot."""
    _log_safely(chat_id=chat_id, user_input=f"[invite] {step}", output="", summary={}, kind="invite")


async def _handle_unauthorized(
    update: Update,
    chat_id: str,
    cmd: str,
    arg: str,
    raw_text: str,
) -> None:
    if not INVITE_CODE:
        _log_invite(chat_id, "no_code_mode")
        await _reply_chunks(
            update,
            f"Chat id của anh/chị là {chat_id}. Anh/chị gửi id này cho nhóm để được cấp quyền dùng thử.",
        )
        return

    if _is_non_private_chat(update):
        _log_invite(chat_id, "group")
        await _reply_chunks(
            update,
            "Kích hoạt bằng mã mời chỉ dùng được khi nhắn riêng 1-1 với em. "
            "Anh/chị mở chat riêng với em rồi nhập mã mời giúp em nhé.",
        )
        return

    if cmd in ("/help", "/huongdan") or (cmd in ("/start", "/join") and not arg):
        _prompted_chats.add(chat_id)
        _log_invite(chat_id, "prompt")
        await _reply_chunks(update, _invite_prompt_text(update))
        return

    candidate = arg if cmd in ("/start", "/join") else raw_text
    if _is_invite_throttled(chat_id):
        _log_invite(chat_id, "throttled")
        await _reply_chunks(
            update,
            "Anh/chị đã nhập sai mã mời quá nhiều lần. Anh/chị thử lại sau ít phút giúp em nhé.",
        )
        return

    if _verify_invite_code(candidate):
        await _grant_access(chat_id)
        _log_invite(chat_id, "activated")
        title = _format_doctor_title(_extract_display_name(update))
        await _reply_chunks(
            update,
            ACTIVATED_TEXT.format(title=title),
        )
        return

    _record_invite_failure(chat_id)
    if cmd not in ("/start", "/join") and chat_id not in _prompted_chats:
        _prompted_chats.add(chat_id)
        _log_invite(chat_id, "prompt")
        await _reply_chunks(update, _invite_prompt_text(update))
        return

    _prompted_chats.add(chat_id)
    _log_invite(chat_id, "wrong")
    await _reply_chunks(
        update,
        "Mã mời chưa đúng ạ. Anh/chị kiểm tra lại và gửi đúng mã mời nhóm đã cung cấp giúp em.",
    )


# ------------------------------------------------------------------ định dạng bản tin (issue #31)
# Chỉ tách dòng và thêm câu dẫn; không bỏ, không sửa chữ nào của agent (mã rule, nguồn, câu chân trang).
# Không nhận ra cấu trúc hoặc lỗi bất kỳ → gửi nguyên output gốc.
def _log_safely(**kwargs: Any) -> None:
    """Ghi log nhưng không bao giờ ném lỗi (đĩa đầy, quyền ghi…): handler gọi hàm này trước khi gửi,
    nên log lỗi không làm BS mất bản tin đã tính xong (review PR #33)."""
    try:
        log_turn(**kwargs)
    except Exception as exc:
        print(f"[warn] ghi log thất bại: {redact(f'{type(exc).__name__}: {exc}')}")


async def _reply_chunks(update: Update, text: str) -> None:
    """Gửi từng đoạn; lỗi gửi thì thử lại tối đa SEND_ATTEMPTS lần (issue #32 A). Hết lượt thì dừng, ghi
    kind="send_error" để đối chiếu log khi BS báo miss tin. Lỗi do timeout sau khi Zalo đã nhận có thể làm BS
    nhận một đoạn hai lần — chấp nhận, vì trùng ít hại hơn mất."""
    msg = update.message
    if msg is None:
        return
    for chunk in split_message(text):
        for attempt in range(1, SEND_ATTEMPTS + 1):
            try:
                await msg.reply_text(chunk)
                break
            except Exception as exc:
                err = redact(f"{type(exc).__name__}: {exc}")
                print(f"[warn] gửi phản hồi thất bại (lần {attempt}/{SEND_ATTEMPTS}): {err}")
                if attempt == SEND_ATTEMPTS:
                    _log_safely(chat_id=str(_extract_chat_id(update) or ""), user_input="", output="",
                                summary={}, error=err, kind="send_error")
                    return
                await asyncio.sleep(SEND_RETRY_SEC)


def _guarded(handler):
    """Bọc handler để lỗi bất ngờ không lọt ra `_polling_loop` của SDK (issue #32): SDK gọi `process_update`
    ngoài khối try, một lỗi ở đó làm dừng hẳn polling và bot im với mọi tin tới khi khởi động lại."""

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await handler(update, context)
        except Exception as exc:
            err = redact(f"{type(exc).__name__}: {exc}")
            print(f"[error] handler {handler.__name__}: {err}")
            _log_safely(chat_id=str(_extract_chat_id(update) or ""), user_input="", output="",
                        summary={}, error=err, kind="handler_error")
            try:
                await _reply_chunks(update, ERROR_TEXT)
            except Exception:
                pass

    wrapper._guarded = True
    return wrapper


@_guarded
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id in ALLOWED_CHAT_IDS:
        await _reply_chunks(update, START_TEXT)
        return
    raw_text = (update.message.text or "").strip() if update.message else ""
    cmd, arg = _parse_command(raw_text)
    if not arg and getattr(context, "args", None):
        arg = " ".join(str(a) for a in context.args).strip()
    await _handle_unauthorized(update, chat_id, cmd or "/start", arg, raw_text)


@_guarded
async def on_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id in ALLOWED_CHAT_IDS:
        await _reply_chunks(
            update,
            "Tài khoản của anh/chị đã được kích hoạt sẵn rồi ạ. Anh/chị gửi ca ngay được nhé.",
        )
        return
    raw_text = (update.message.text or "").strip() if update.message else ""
    _, arg = _parse_command(raw_text)
    if not arg and getattr(context, "args", None):
        arg = " ".join(str(a) for a in context.args).strip()
    await _handle_unauthorized(update, chat_id, "/join", arg, raw_text)


@_guarded
async def on_new_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        raw_text = (update.message.text or "").strip() if update.message else ""
        await _handle_unauthorized(update, chat_id, "", "", raw_text)
        return
    _conv(chat_id).new_case()
    # Ghi ranh giới ca: thiếu dòng này thì log không cho biết vì sao tin sau không ghép (log VM 28/11 08:30–08:34).
    _log_safely(chat_id=chat_id, user_input="/moi", output=NEW_CASE_TEXT, summary={}, kind="new_case")
    await _reply_chunks(update, NEW_CASE_TEXT)


@_guarded
async def on_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/huongdan: cách dùng đầy đủ (tin kích hoạt chỉ in bản ngắn)."""
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "/huongdan", "", "")
        return
    await _reply_chunks(update, USAGE_TEXT)


@_guarded
async def on_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sai <lý do>: ghi góp ý vào log (đã che PII), không gọi agent, không đụng ca đang chờ / ca vừa xong."""
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None:
        return
    raw_text = (update.message.text or "").strip()
    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "", "", raw_text)
        return
    masked, _ = mask_identifiers(raw_text)
    _log_safely(chat_id=chat_id, user_input=masked, output=FEEDBACK_ACK, summary={}, kind="feedback")
    await _reply_chunks(update, FEEDBACK_ACK)


@_guarded
async def on_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ảnh / sticker / tin thoại: bot chỉ đọc chữ — trả một câu hướng dẫn thay vì im lặng. Chat lạ thì bỏ qua."""
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None:
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        _log_invite(chat_id, "non_text")   # vẫn không trả lời người lạ, chỉ đếm
        return
    _log_safely(chat_id=chat_id, user_input="[non_text]", output=NON_TEXT_TEXT, summary={}, kind="non_text")
    await _reply_chunks(update, NON_TEXT_TEXT)


async def _reply_small_talk(update: Update, chat_id: str, text: str, kind: str) -> None:
    """Tin xã giao ("cảm ơn", "chào em"): đáp ngay, không gọi agent, không đụng ca đang chờ.
    Chào lại trong GREET_AGAIN_SEC → câu ngắn; hỏi "làm được gì" luôn nhận bản giới thiệu đủ."""
    again = kind == "greet" and _conv(chat_id).greet(time.monotonic())
    reply_text = AGENT_TEXT["HELLO_AGAIN"] if again else small_talk_text(kind)
    _log_safely(chat_id=chat_id, user_input=text, output=reply_text, summary={}, error="", kind="small_talk")
    await _reply_chunks(update, reply_text)


async def _reply_detail(update: Update, chat_id: str) -> None:
    """ "chi tiết": in lại bản tin đã lưu của ca gần nhất ở dạng đủ — không gọi lại agent."""
    case = _conv(chat_id).recent(time.monotonic())
    output = render_detail(case.reply) if case else NO_DETAIL_TEXT
    if case:
        _log_safely(chat_id=chat_id, user_input="chi tiết", output=output, summary={}, kind="detail")
    await _reply_chunks(update, output)


async def _reply_case(update: Update, chat_id: str, text: str) -> None:
    masked, had_ids = mask_identifiers(text)
    conv = _conv(chat_id)
    summary: dict[str, Any] = {}
    case_status = "new"
    try:
        # Không cần khoá ở đây: _spawn_update đã cho tin cùng chat chạy lần lượt (PR #50).
        case_text, case_status = conv.compose(masked, time.monotonic())
        async with _agent_slots:
            reply, summary = await asyncio.to_thread(run_agent, case_text)
        conv.remember(case_text, reply, time.monotonic())
        repeat_miss = conv.count_miss(reply)
    except Exception as exc:
        err_msg = redact(f"{type(exc).__name__}: {exc}")
        print(f"[error] {err_msg}")
        _log_safely(chat_id=chat_id, user_input=masked, output="", summary=summary, error=err_msg)
        # Ca chờ đã bị bỏ trong compose(): BS gửi lại tin bổ sung sẽ thành ca mới, nên phải báo ngay ở đây,
        # không thì lần sau ra ✅ mà không có dòng ⏱️.
        await _reply_chunks(update, f"{DROPPED_NOTE}\n{ERROR_TEXT}" if case_status == "dropped" else ERROR_TEXT)
        return
    output = compose_reply(reply, repeat_miss=repeat_miss, case_status=case_status, had_ids=had_ids)
    _log_safely(chat_id=chat_id, user_input=masked, output=output, summary=summary, error="",
                drop_input=PII_WARNING in output)
    await _reply_chunks(update, output)


# Lệnh BS gõ: đăng ký với SDK (main) VÀ định tuyến trong on_text từ cùng một bảng — SDK có lúc giao lệnh cho on_text.
COMMANDS = {
    "/start": on_start, "/help": on_start, "/join": on_join, "/moi": on_new_case,
    "/huongdan": on_usage, "/sai": on_feedback,
}


@_guarded
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None or not update.message.text:
        return
    text = update.message.text.strip()
    command = COMMANDS.get(_parse_command(text)[0])
    if command:
        await command(update, context)
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "", "", text)
        return
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

    kind = small_talk_kind(text)
    if kind:
        await _reply_small_talk(update, chat_id, text, kind)
    elif DETAIL_RE.match(text):
        await _reply_detail(update, chat_id)
    else:
        await _reply_case(update, chat_id, text)


async def _process_in_chat_order(app: Any, update: Update) -> None:
    key = str(_extract_chat_id(update) or "")
    lock = _chat_locks.setdefault(key, asyncio.Lock())
    _chat_users[key] = _chat_users.get(key, 0) + 1
    try:
        async with lock:
            await app.process_update(update)
    except Exception as exc:   # handler đã _guarded; đây chỉ chặn lỗi lọt ra từ chính SDK
        print(f"[error] process_update: {redact(f'{type(exc).__name__}: {exc}')}")
    finally:
        # Không dựa vào lock.locked(): vừa nhả khoá thì task chờ kế tiếp chưa kịp giữ lại, xoá lúc đó
        # sẽ làm tin tới sau tạo khoá mới và chạy chồng (review PR #50).
        _chat_users[key] -= 1
        if _chat_users[key] == 0:
            _chat_users.pop(key, None)
            _chat_locks.pop(key, None)


def _spawn_update(app: Any, update: Update) -> asyncio.Task:
    """Chạy mỗi tin thành một task riêng: chat khác nhau song song, cùng chat lần lượt."""
    task = asyncio.create_task(_process_in_chat_order(app, update))
    _inflight.add(task)
    task.add_done_callback(_inflight.discard)
    return task


async def _poll_forever(app: Any) -> None:
    """Thay app.run_polling(): vòng của SDK `await process_update` từng tin một, 200 BS nhắn cùng lúc
    sẽ phải xếp hàng. Ở đây lấy tin rồi giao task ngay, quay lại lấy tin kế tiếp."""
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=AGENT_CONCURRENCY))
    await app.bot.initialize()
    try:
        while True:
            try:
                update = await app.bot.get_update(timeout=30)
            except Exception as exc:
                print(f"[warn] lấy tin thất bại: {redact(f'{type(exc).__name__}: {exc}')}")
                await asyncio.sleep(1)
                continue
            if update:
                _spawn_update(app, update)
            else:
                await asyncio.sleep(1)
    finally:
        await app.bot.shutdown()


def main() -> None:
    if not TOKEN:
        sys.exit(
            "Thiếu ZALO_BOT_TOKEN trong file .env ở gốc repo. "
            "Xem hướng dẫn tạo bot và cấu hình tại docs/zalo-bot.md."
        )

    app = ApplicationBuilder().token(TOKEN).build()
    for command, handler in COMMANDS.items():
        app.add_handler(CommandHandler(command.lstrip("/"), handler))
    app.add_handler(MessageHandler(filters.TEXT, on_text))
    app.add_handler(MessageHandler(~filters.TEXT, on_non_text))

    provider = (os.environ.get("MODEL_PROVIDER") or "fake").strip()
    model_name = (os.environ.get("MODEL_NAME") or "—").strip()
    invite_state = "on" if INVITE_CODE else "off"
    print(
        f"Zalo Bot RHM đang chạy (polling) · allowlist={len(ALLOWED_CHAT_IDS)} "
        f"(env={len(ENV_ALLOWED_CHAT_IDS)}, saved={len(SAVED_CHAT_IDS)}) · "
        f"invite={invite_state} · model={provider}/{model_name} · concurrency={AGENT_CONCURRENCY}"
    )
    asyncio.run(_poll_forever(app))


if __name__ == "__main__":
    main()
