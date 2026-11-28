"""Bộ dựng chung cho test bot: stub SDK `zalo_bot` khi chưa cài, nạp bot/zalo_bot.py, bản tin mẫu, Update giả.

Không phải file test (không có tiền tố test_). Test import: `from bot._testkit import …` (chạy từ gốc repo).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import types


def _ensure_zalo_bot_stub() -> None:
    if "zalo_bot" in sys.modules:
        return
    try:
        import zalo_bot  # noqa: F401
        return
    except ImportError:
        pass

    zalo_pkg = types.ModuleType("zalo_bot")

    class Update:
        pass

    zalo_pkg.Update = Update

    constants_mod = types.ModuleType("zalo_bot.constants")

    class ChatAction:
        TYPING = "typing"

    constants_mod.ChatAction = ChatAction

    ext_mod = types.ModuleType("zalo_bot.ext")

    class _DummyApp:
        def add_handler(self, *args, **kwargs):
            return None

        def run_polling(self, *args, **kwargs):
            return None

    class ApplicationBuilder:
        def token(self, _token: str):
            return self

        def build(self):
            return _DummyApp()

    class CommandHandler:
        def __init__(self, command, callback):
            self.command = command
            self.callback = callback

    class ContextTypes:
        DEFAULT_TYPE = object

    class MessageHandler:
        def __init__(self, filter_obj, callback):
            self.filter_obj = filter_obj
            self.callback = callback

    class _Filters:
        TEXT = "TEXT"

    ext_mod.ApplicationBuilder = ApplicationBuilder
    ext_mod.CommandHandler = CommandHandler
    ext_mod.ContextTypes = ContextTypes
    ext_mod.MessageHandler = MessageHandler
    ext_mod.filters = _Filters()

    sys.modules["zalo_bot"] = zalo_pkg
    sys.modules["zalo_bot.constants"] = constants_mod
    sys.modules["zalo_bot.ext"] = ext_mod


def _has_real_zalo_bot_sdk() -> bool:
    # PathFinder bỏ qua sys.modules: stub của _ensure_zalo_bot_stub() không có __spec__,
    # importlib.util.find_spec sẽ ném ValueError và không thấy được SDK thật đã cài.
    bot_dir = str(Path(__file__).resolve().parent)
    search = [p for p in sys.path if p and str(Path(p).resolve()) != bot_dir]
    spec = importlib.machinery.PathFinder.find_spec("zalo_bot", search)
    return spec is not None and spec.origin is not None and str(Path(spec.origin).resolve()) != str(
        (Path(__file__).resolve().parent / "zalo_bot.py").resolve()
    )


def _load_bot_module():
    _ensure_zalo_bot_stub()
    bot_path = Path(__file__).resolve().parent / "zalo_bot.py"
    spec = importlib.util.spec_from_file_location("zalo_bot_under_test", bot_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod   # dataclass cần tìm được module của mình trong sys.modules
    spec.loader.exec_module(mod)
    return mod


bot_mod = _load_bot_module()
from reply import Alert, Reply  # noqa: E402  (bot đã thêm codebase/ vào sys.path)
import reply as reply_mod  # noqa: E402


def _text_reply(text: str = "fake output", needs_more: bool = False) -> Reply:
    return Reply.text_only(text, needs_more=needs_more)


HIGH_ALERT = Alert("DDI-001", "HIGH", "[DDI-001] Ibuprofen + Warfarin → Tránh phối hợp, theo dõi INR",
                   "DDInter (Major: X)",
                   "[DDI-001] Ibuprofen + Warfarin → Tránh phối hợp, theo dõi INR. (Vì: NSAID ức chế tiểu cầu). "
                   "Nguồn: DDInter (Major: X).")
MODERATE_ALERT = Alert("DDI-029", "MODERATE", "[DDI-029] Paracetamol + Warfarin: tăng INR", "DDInter (Moderate: Y)",
                       "[DDI-029] Paracetamol + Warfarin → Dùng ngắn ngày. (Vì: tăng INR). Nguồn: DDInter (Moderate: Y).",
                       compact_head="[DDI-029] Paracetamol + Warfarin")


class _FakeUser:
    def __init__(self, display_name: str | None = None, is_bot: bool = False):
        self.display_name = display_name
        self.is_bot = is_bot


class _FakeChat:
    def __init__(self, chat_id: str, chat_type: str | None = None):
        self.id = chat_id
        if chat_type is not None:
            self.type = chat_type
            self.chat_type = chat_type


class _FakeMessage:
    def __init__(
        self,
        chat_id: str,
        text: str,
        display_name: str | None = None,
        is_bot: bool = False,
        chat_type: str | None = None,
    ):
        self.chat = _FakeChat(chat_id, chat_type=chat_type)
        self.text = text
        self.from_user = _FakeUser(display_name=display_name, is_bot=is_bot)
        self.replies: list[str] = []

    async def reply_text(self, chunk: str) -> None:
        self.replies.append(chunk)


class _FakeUpdate:
    def __init__(
        self,
        chat_id: str,
        text: str,
        display_name: str | None = None,
        chat_type: str | None = None,
    ):
        self.message = _FakeMessage(chat_id, text, display_name=display_name, chat_type=chat_type)
        self.effective_user = self.message.from_user


class _FakeBot:
    def __init__(self):
        self.actions: list[tuple[str, str]] = []

    async def send_chat_action(self, chat_id: str, action: str) -> None:
        self.actions.append((chat_id, action))


class _FakeContext:
    def __init__(self, args: list[str] | None = None):
        self.args = args or []
        self.bot = _FakeBot()
