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
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CODEBASE_DIR = ROOT / "codebase"
if str(CODEBASE_DIR) not in sys.path:
    sys.path.insert(0, str(CODEBASE_DIR))

import tracing  # noqa: E402
from agent import answer  # noqa: E402  (import agent -> ai.py tự nạp .env ở gốc repo)

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

TOKEN = os.environ.get("ZALO_BOT_TOKEN", "").strip()
ALLOWED_CHAT_IDS = {
    part.strip()
    for part in (os.environ.get("ZALO_ALLOWED_CHAT_IDS") or "").split(",")
    if part.strip()
}

# tracing dùng biến toàn cục nên chỉ cho phép một ca chạy qua answer() tại một thời điểm.
_agent_lock = asyncio.Lock()

START_TEXT = (
    "Xin chào! Đây là trợ lý tra cứu an toàn trước thủ thuật & kê đơn RHM (bản thử hackathon).\n\n"
    "Cách dùng: nhắn 1 tin gồm đủ 5 ý (nếu có): bệnh nền, dị ứng, thuốc đang dùng, "
    "thủ thuật dự kiến và thuốc định kê.\n\n"
    "Lưu ý bắt buộc:\n"
    "• Chỉ dùng ca giả lập hoặc đã ẩn danh — KHÔNG gửi họ tên, SĐT, mã hồ sơ hay ảnh đơn thuốc thật của BN.\n"
    "• Bot chỉ hỗ trợ đối chiếu cảnh báo kèm nguồn; không kê đơn, không tư vấn liều, BS là người quyết định.\n\n"
    "Ví dụ:\n"
    "BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. Định kê Augmentin + Ibuprofen"
)


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


def _chat_hash(chat_id: str) -> str:
    return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:10]


def log_turn(
    *,
    chat_id: str,
    user_input: str,
    output: str,
    summary: dict[str, Any],
    error: str = "",
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    log_path = LOG_DIR / f"{now.strftime('%Y%m%d')}.jsonl"
    models = summary.get("models") or []
    record = {
        "ts": now.isoformat(),
        "chat": _chat_hash(chat_id),
        "input": user_input,
        "output": output,
        "model": ", ".join(models) if models else "",
        "tokens_in": int(summary.get("tokens_in") or 0),
        "tokens_out": int(summary.get("tokens_out") or 0),
        "error": error,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_agent(text: str) -> tuple[str, dict[str, Any]]:
    tracing.begin("zalo")
    try:
        res = answer(text)
        if isinstance(res, dict):
            output = str(res.get("output") or "")
        else:
            output = str(res or "")
    finally:
        summary, _ = tracing.end()
    return output, summary


def _extract_chat_id(update: Update) -> str | None:
    msg = update.message
    if msg is None or msg.chat is None:
        return None
    if msg.from_user and msg.from_user.is_bot:
        return None
    return str(msg.chat.id) if msg.chat.id is not None else None


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
    await _reply_chunks(
        update,
        f"Chat id của bạn là {chat_id}. Gửi id này cho nhóm để được cấp quyền dùng thử.",
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None or update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    if cmd in ("/start", "/help"):
        await on_start(update, context)
        return

    if chat_id not in ALLOWED_CHAT_IDS:
        await _reply_chunks(
            update,
            f"Chat id của bạn là {chat_id}. Gửi id này cho nhóm để được cấp quyền dùng thử.",
        )
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

    output = ""
    summary: dict[str, Any] = {}
    err_msg = ""
    try:
        async with _agent_lock:
            output, summary = await asyncio.to_thread(run_agent, text)
    except Exception as exc:
        err_msg = redact(f"{type(exc).__name__}: {exc}")
        print(f"[error] {err_msg}")
        log_turn(chat_id=chat_id, user_input=text, output="", summary=summary, error=err_msg)
        await _reply_chunks(update, "Xin lỗi, hệ thống tra cứu đang lỗi, anh/chị thử lại sau ít phút.")
        return

    log_turn(chat_id=chat_id, user_input=text, output=output, summary=summary, error="")
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
    app.add_handler(MessageHandler(filters.TEXT, on_text))

    provider = (os.environ.get("MODEL_PROVIDER") or "fake").strip()
    model_name = (os.environ.get("MODEL_NAME") or "—").strip()
    print(
        f"Zalo Bot RHM đang chạy (polling) · allowlist={len(ALLOWED_CHAT_IDS)} chat_id · "
        f"model={provider}/{model_name}"
    )
    app.run_polling()


if __name__ == "__main__":
    main()
