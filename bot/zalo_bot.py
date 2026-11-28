"""Lớp vỏ mỏng cho Zalo Bot (long polling) — chỉ nhận tin, gọi agent.answer(text) và trả lời.

Không chứa logic y khoa hay tra cứu; `run.py`, `eval/run_eval.py`, `cost/simulate.py` không import file này.
Chạy từ thư mục gốc repo:
    bot/.venv/bin/python bot/zalo_bot.py

Hướng dẫn tạo bot mới và vận hành chi tiết: xem `docs/zalo-bot.md`.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any

BOT_DIR = Path(__file__).resolve().parent
ROOT = BOT_DIR.parent
CODEBASE_DIR = ROOT / "codebase"
# Tránh bot/zalo_bot.py tự che khuất thư viện `zalo_bot` khi chạy trực tiếp `python bot/zalo_bot.py`.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != BOT_DIR]
if str(CODEBASE_DIR) not in sys.path:
    sys.path.insert(0, str(CODEBASE_DIR))

import tracing  # noqa: E402
from agent import (  # noqa: E402  (import agent -> ai.py tự nạp .env ở gốc repo)
    TEXT as AGENT_TEXT, answer, is_no_entity_reply, small_talk_kind, small_talk_reply,
)

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
MAX_PENDING_CHARS = 4000
NEW_CASE_TEXT = "Đã bắt đầu ca mới."
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
# Kế hoạch giao tiếp Trung duyệt 28/11 (docs/design.md §7, §9).
GREET_AGAIN_SEC = 12 * 3600   # chào lại trong 12 giờ → câu ngắn HELLO_AGAIN (mốc đề xuất, không có nguồn)
DETAIL_RE = re.compile(r"^\s*(?:xem\s+|cho\s+(?:em\s+|mình\s+|minh\s+)?xem\s+)?chi\s+ti[eếê]t"
                       r"(?:\s+(?:đi|di|nhé|nhe|nha|ạ|a))?\s*[.!?]*\s*$", re.IGNORECASE)
DETAIL_HINT = "(Nhắn \"chi tiết\" trong 10 phút để xem hướng xử trí các mục 🟡.)"
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

# tracing dùng biến toàn cục nên chỉ cho phép một ca chạy qua answer() tại một thời điểm.
_agent_lock = asyncio.Lock()
_allowlist_lock = asyncio.Lock()
_prompted_chats: set[str] = set()
_failed_attempts: dict[str, list[float]] = {}
_pending: dict[str, tuple[str, float]] = {}
# Ca vừa xong (needs_more=False) — chỉ ghép khi BS mở đầu tin bằng "thêm"/"bổ sung" (design §9, 28/11).
_last_case: dict[str, tuple[str, float]] = {}
_last_greet: dict[str, float] = {}   # giờ chào gần nhất theo chat (RAM, mất khi restart)
_misses: dict[str, int] = {}         # số lần liên tiếp không nhận ra thực thể nào

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
    "• \"chi tiết\" — xem hướng xử trí các mục 🟡 của ca vừa xong.\n"
    "• /sai <lý do> — báo cảnh báo sai hoặc không hữu ích.\n\n"
    "Ví dụ:\n"
    "BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen"
)
START_TEXT = f"Xin chào! {USAGE_TEXT}"
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
    """kind: "case" · "small_talk" · "feedback" (/sai) · "detail" ("chi tiết") — bot/log_stats.py đếm theo trường này."""
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


def _compose_case(chat_id: str, text: str, now: float | None = None) -> tuple[str, str]:
    """Ghép tin mới vào ca đang chờ bổ sung của đúng chat nếu chưa quá PENDING_TTL_SEC (design §9).

    Trả (chữ gửi agent, trạng thái): "new" không có ca chờ · "merged" đã ghép ·
    "dropped" có ca chờ nhưng quá hạn / quá dài nên bỏ — phải báo BS, vì tin bổ sung đứng một mình
    có thể thiếu thuốc nền và mất cảnh báo HIGH (vd warfarin rồi "Định kê ibuprofen").
    """
    ts = time.monotonic() if now is None else now
    if NEW_PATIENT_RE.match(text or ""):
        return text, "new"
    store = _pending
    pending = _pending.get(chat_id)
    if pending is None and FOLLOW_UP_RE.match(text or ""):
        store, pending = _last_case, _last_case.get(chat_id)
    if pending is None:
        return text, "new"
    old_text, saved_at = pending
    merged = f"{old_text}\nBổ sung: {text}"
    if ts - saved_at > PENDING_TTL_SEC or len(merged) > MAX_PENDING_CHARS:
        store.pop(chat_id, None)
        return text, "dropped"
    return merged, "merged"


def _remember_case(chat_id: str, case_text: str, needs_more: bool) -> None:
    if needs_more:
        _pending[chat_id] = (case_text, time.monotonic())
        _last_case.pop(chat_id, None)
    else:
        _pending.pop(chat_id, None)
        _last_case[chat_id] = (case_text, time.monotonic())


def run_agent(text: str, detail: bool = False) -> tuple[str, dict[str, Any], bool]:
    tracing.begin("zalo")
    needs_more = False
    try:
        res = answer(text, detail=True) if detail else answer(text)
        if isinstance(res, dict):
            output = str(res.get("output") or "")
            needs_more = res.get("needs_more") is True
        else:
            output = str(res or "")
    finally:
        summary, _ = tracing.end()
    return output, summary, needs_more


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


async def _handle_unauthorized(
    update: Update,
    chat_id: str,
    cmd: str,
    arg: str,
    raw_text: str,
) -> None:
    if not INVITE_CODE:
        await _reply_chunks(
            update,
            f"Chat id của anh/chị là {chat_id}. Anh/chị gửi id này cho nhóm để được cấp quyền dùng thử.",
        )
        return

    if _is_non_private_chat(update):
        await _reply_chunks(
            update,
            "Kích hoạt bằng mã mời chỉ dùng được khi nhắn riêng 1-1 với em. "
            "Anh/chị mở chat riêng với em rồi nhập mã mời giúp em nhé.",
        )
        return

    if cmd in ("/help", "/huongdan") or (cmd in ("/start", "/join") and not arg):
        _prompted_chats.add(chat_id)
        await _reply_chunks(update, _invite_prompt_text(update))
        return

    candidate = arg if cmd in ("/start", "/join") else raw_text
    if _is_invite_throttled(chat_id):
        await _reply_chunks(
            update,
            "Anh/chị đã nhập sai mã mời quá nhiều lần. Anh/chị thử lại sau ít phút giúp em nhé.",
        )
        return

    if _verify_invite_code(candidate):
        await _grant_access(chat_id)
        title = _format_doctor_title(_extract_display_name(update))
        await _reply_chunks(
            update,
            ACTIVATED_TEXT.format(title=title),
        )
        return

    _record_invite_failure(chat_id)
    if cmd not in ("/start", "/join") and chat_id not in _prompted_chats:
        _prompted_chats.add(chat_id)
        await _reply_chunks(update, _invite_prompt_text(update))
        return

    _prompted_chats.add(chat_id)
    await _reply_chunks(
        update,
        "Mã mời chưa đúng ạ. Anh/chị kiểm tra lại và gửi đúng mã mời nhóm đã cung cấp giúp em.",
    )


async def _reply_chunks(update: Update, text: str) -> None:
    msg = update.message
    if msg is None:
        return
    for chunk in split_message(text):
        try:
            await msg.reply_text(chunk)
        except Exception as exc:
            print(f"[warn] gửi phản hồi thất bại: {redact(f'{type(exc).__name__}: {exc}')}")
            break


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


async def on_new_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        raw_text = (update.message.text or "").strip() if update.message else ""
        await _handle_unauthorized(update, chat_id, "", "", raw_text)
        return
    _pending.pop(chat_id, None)
    _last_case.pop(chat_id, None)
    _misses.pop(chat_id, None)
    await _reply_chunks(update, NEW_CASE_TEXT)


async def on_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/huongdan: cách dùng đầy đủ (tin kích hoạt chỉ in bản ngắn)."""
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "/huongdan", "", "")
        return
    await _reply_chunks(update, USAGE_TEXT)


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
    log_turn(chat_id=chat_id, user_input=masked, output=FEEDBACK_ACK, summary={}, kind="feedback")
    await _reply_chunks(update, FEEDBACK_ACK)


def _recent_case(chat_id: str, now: float | None = None) -> str | None:
    """Ca để xem "chi tiết": ca đang chờ bổ sung, nếu không thì ca vừa xong — chỉ trong PENDING_TTL_SEC."""
    ts = time.monotonic() if now is None else now
    for store in (_pending, _last_case):
        item = store.get(chat_id)
        if item and ts - item[1] <= PENDING_TTL_SEC:
            return item[0]
    return None


async def _reply_detail(update: Update, chat_id: str) -> None:
    case_text = _recent_case(chat_id)
    if case_text is None:
        await _reply_chunks(update, NO_DETAIL_TEXT)
        return
    try:
        async with _agent_lock:
            output, summary, _ = await asyncio.to_thread(run_agent, case_text, True)
    except Exception as exc:
        err_msg = redact(f"{type(exc).__name__}: {exc}")
        print(f"[error] {err_msg}")
        log_turn(chat_id=chat_id, user_input="chi tiết", output="", summary={}, error=err_msg, kind="detail")
        await _reply_chunks(update, "Xin lỗi, hệ thống tra cứu đang lỗi, anh/chị thử lại sau ít phút.")
        return
    log_turn(chat_id=chat_id, user_input="chi tiết", output=output, summary=summary, kind="detail")
    await _reply_chunks(update, output)


async def on_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ảnh / sticker / tin thoại: bot chỉ đọc chữ — trả một câu hướng dẫn thay vì im lặng. Chat lạ thì bỏ qua."""
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None or chat_id not in ALLOWED_CHAT_IDS:
        return
    await _reply_chunks(update, NON_TEXT_TEXT)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    cmd, _ = _parse_command(text)
    if cmd in ("/start", "/help"):
        await on_start(update, context)
        return
    if cmd == "/join":
        await on_join(update, context)
        return
    if cmd == "/moi":
        await on_new_case(update, context)
        return
    if cmd == "/huongdan":
        await on_usage(update, context)
        return
    if cmd == "/sai":
        await on_feedback(update, context)
        return

    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "", "", text)
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

    # Tin xã giao ("cảm ơn", "chào em"): đáp ngay, không ghép vào ca đang chờ, không đụng tới pending.
    # Chào lại trong GREET_AGAIN_SEC → câu ngắn; hỏi "làm được gì" luôn nhận bản giới thiệu đủ.
    small_talk = small_talk_reply(text)
    if small_talk:
        if small_talk_kind(text) == "greet":
            now = time.monotonic()
            last = _last_greet.get(chat_id)
            if last is not None and now - last <= GREET_AGAIN_SEC:
                small_talk = AGENT_TEXT["HELLO_AGAIN"]
            _last_greet[chat_id] = now
        log_turn(chat_id=chat_id, user_input=text, output=small_talk, summary={}, error="", kind="small_talk")
        await _reply_chunks(update, small_talk)
        return

    if DETAIL_RE.match(text):
        await _reply_detail(update, chat_id)
        return

    masked, had_ids = mask_identifiers(text)
    output = ""
    summary: dict[str, Any] = {}
    err_msg = ""
    case_status = "new"
    try:
        async with _agent_lock:
            case_text, case_status = _compose_case(chat_id, masked)
            output, summary, needs_more = await asyncio.to_thread(run_agent, case_text)
            _remember_case(chat_id, case_text, needs_more)
            if is_no_entity_reply(output):
                _misses[chat_id] = _misses.get(chat_id, 0) + 1
                if _misses[chat_id] >= 2:   # lần thứ 2 liên tiếp: đưa câu mẫu thay cho Q1 (design §9)
                    output = output.replace(AGENT_TEXT["Q1"], AGENT_TEXT["REPAIR"])
            else:
                _misses.pop(chat_id, None)
            if AGENT_TEXT["MODERATE_HEADER"].split(":")[0] in output:   # có khối 🟡 gọn → mời xem chi tiết
                output = f"{output}\n{DETAIL_HINT}"
            if not needs_more:
                output = f"{output}\n{FOLLOW_UP_HINT}"
    except Exception as exc:
        err_msg = redact(f"{type(exc).__name__}: {exc}")
        print(f"[error] {err_msg}")
        log_turn(chat_id=chat_id, user_input=masked, output="", summary=summary, error=err_msg)
        error_text = "Xin lỗi, hệ thống tra cứu đang lỗi, anh/chị thử lại sau ít phút."
        if case_status == "dropped":
            # Ca chờ đã bị xoá trong _compose_case: BS gửi lại tin bổ sung sẽ thành ca mới,
            # nên phải báo ngay ở đây, không thì lần sau ra ✅ mà không có dòng ⏱️.
            error_text = f"{DROPPED_NOTE}\n{error_text}"
        await _reply_chunks(update, error_text)
        return

    if had_ids and not output.startswith(PII_WARNING):
        output = f"{PII_WARNING}\n{output}"
    if case_status == "merged":
        output = f"{output}\n{MERGED_NOTE}"
    elif case_status == "dropped":
        # Đặt lên đầu: BS phải thấy trước khi đọc dòng ✅ của ca thiếu dữ kiện.
        output = f"{DROPPED_NOTE}\n{output}"
    log_turn(chat_id=chat_id, user_input=masked, output=output, summary=summary, error="",
             drop_input=PII_WARNING in output)
    await _reply_chunks(update, output)


def main() -> None:
    if not TOKEN:
        sys.exit(
            "Thiếu ZALO_BOT_TOKEN trong file .env ở gốc repo. "
            "Xem hướng dẫn tạo bot và cấu hình tại docs/zalo-bot.md."
        )

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help", on_start))
    app.add_handler(CommandHandler("join", on_join))
    app.add_handler(CommandHandler("moi", on_new_case))
    app.add_handler(CommandHandler("huongdan", on_usage))
    app.add_handler(CommandHandler("sai", on_feedback))
    app.add_handler(MessageHandler(filters.TEXT, on_text))
    app.add_handler(MessageHandler(~filters.TEXT, on_non_text))

    provider = (os.environ.get("MODEL_PROVIDER") or "fake").strip()
    model_name = (os.environ.get("MODEL_NAME") or "—").strip()
    invite_state = "on" if INVITE_CODE else "off"
    print(
        f"Zalo Bot RHM đang chạy (polling) · allowlist={len(ALLOWED_CHAT_IDS)} "
        f"(env={len(ENV_ALLOWED_CHAT_IDS)}, saved={len(SAVED_CHAT_IDS)}) · "
        f"invite={invite_state} · model={provider}/{model_name}"
    )
    app.run_polling()


if __name__ == "__main__":
    main()
