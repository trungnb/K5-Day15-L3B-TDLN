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
from agent import TEXT as AGENT_TEXT, answer  # noqa: E402  (import agent -> ai.py tự nạp .env ở gốc repo)

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
MERGED_NOTE = "(Em đã ghép với tin trước của ca này. Nếu là BN khác, nhắn /moi rồi gửi lại.)"

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

_DOCTOR_PREFIX_RE = re.compile(
    r"^(?:(?:bs|dr)(?:\.|\s|$)|(?:bác|bac)\s*s[ĩi](?:\s|$))",
    re.IGNORECASE,
)

USAGE_TEXT = (
    "Đây là trợ lý tra cứu an toàn trước thủ thuật & kê đơn RHM (bản thử hackathon).\n\n"
    "Cách dùng: nhắn 1 tin gồm đủ 5 ý (nếu có): bệnh nền, dị ứng, thuốc đang dùng, "
    "thủ thuật dự kiến và thuốc định kê.\n\n"
    "Lưu ý bắt buộc:\n"
    "• Chỉ dùng ca giả lập hoặc đã ẩn danh — KHÔNG gửi họ tên, SĐT, mã hồ sơ hay ảnh đơn thuốc thật của BN.\n"
    "• Bot chỉ hỗ trợ đối chiếu cảnh báo kèm nguồn; không kê đơn, không tư vấn liều, BS là người quyết định.\n"
    "• Thiếu ý nào bot sẽ hỏi lại, BS nhắn bổ sung trong 10 phút là bot ghép vào ca đang hỏi. "
    "Chuyển sang BN khác thì nhắn /moi.\n\n"
    "Ví dụ:\n"
    "BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen"
)
START_TEXT = f"Xin chào! {USAGE_TEXT}"


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
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    log_path = LOG_DIR / f"{now.strftime('%Y%m%d')}.jsonl"
    models = summary.get("models") or []
    record = {
        "ts": now.isoformat(),
        "chat": _chat_hash(chat_id),
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


def _compose_case(chat_id: str, text: str, now: float | None = None) -> tuple[str, bool]:
    """Ghép tin mới vào ca đang chờ bổ sung của đúng chat nếu chưa quá PENDING_TTL_SEC (design §9)."""
    ts = time.monotonic() if now is None else now
    pending = _pending.get(chat_id)
    if pending is None:
        return text, False
    old_text, saved_at = pending
    merged = f"{old_text}\nBổ sung: {text}"
    if ts - saved_at > PENDING_TTL_SEC or len(merged) > MAX_PENDING_CHARS:
        _pending.pop(chat_id, None)
        return text, False
    return merged, True


def _remember_case(chat_id: str, case_text: str, needs_more: bool) -> None:
    if needs_more:
        _pending[chat_id] = (case_text, time.monotonic())
    else:
        _pending.pop(chat_id, None)


def run_agent(text: str) -> tuple[str, dict[str, Any], bool]:
    tracing.begin("zalo")
    needs_more = False
    try:
        res = answer(text)
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
        f"Chào {title}, BS vui lòng nhập mã mời để bắt đầu sử dụng "
        "trợ lý tra cứu an toàn RHM (chỉ cần nhập 1 lần)."
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
            f"Chat id của bạn là {chat_id}. Gửi id này cho nhóm để được cấp quyền dùng thử.",
        )
        return

    if _is_non_private_chat(update):
        await _reply_chunks(
            update,
            "Tính năng kích hoạt bằng mã mời chỉ hỗ trợ nhắn riêng 1-1 với bot. "
            "BS vui lòng mở chat riêng với bot rồi nhập mã mời.",
        )
        return

    if cmd == "/help" or (cmd in ("/start", "/join") and not arg):
        _prompted_chats.add(chat_id)
        await _reply_chunks(update, _invite_prompt_text(update))
        return

    candidate = arg if cmd in ("/start", "/join") else raw_text
    if _is_invite_throttled(chat_id):
        await _reply_chunks(
            update,
            "BS đã nhập sai mã mời quá nhiều lần. Vui lòng thử lại sau ít phút.",
        )
        return

    if _verify_invite_code(candidate):
        await _grant_access(chat_id)
        title = _format_doctor_title(_extract_display_name(update))
        await _reply_chunks(
            update,
            f"Đã kích hoạt thành công! Chào {title}.\n\n{USAGE_TEXT}",
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
        "Mã mời chưa đúng. BS vui lòng kiểm tra lại và gửi đúng mã mời được nhóm cung cấp.",
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
            "Tài khoản của BS đã được kích hoạt sẵn rồi. BS có thể gửi ca bệnh ngay ạ.",
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
    await _reply_chunks(update, NEW_CASE_TEXT)


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

    if chat_id not in ALLOWED_CHAT_IDS:
        await _handle_unauthorized(update, chat_id, "", "", text)
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

    masked, had_ids = mask_identifiers(text)
    output = ""
    summary: dict[str, Any] = {}
    err_msg = ""
    merged = False
    try:
        async with _agent_lock:
            case_text, merged = _compose_case(chat_id, masked)
            output, summary, needs_more = await asyncio.to_thread(run_agent, case_text)
            _remember_case(chat_id, case_text, needs_more)
    except Exception as exc:
        err_msg = redact(f"{type(exc).__name__}: {exc}")
        print(f"[error] {err_msg}")
        log_turn(chat_id=chat_id, user_input=masked, output="", summary=summary, error=err_msg)
        await _reply_chunks(update, "Xin lỗi, hệ thống tra cứu đang lỗi, anh/chị thử lại sau ít phút.")
        return

    if had_ids and not output.startswith(PII_WARNING):
        output = f"{PII_WARNING}\n{output}"
    if merged:
        output = f"{output}\n{MERGED_NOTE}"
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
    app.add_handler(MessageHandler(filters.TEXT, on_text))

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
