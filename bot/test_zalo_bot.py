"""Unit tests cho cơ chế mã mời, lưu chat_id và lời chào BS của bot/zalo_bot.py."""
from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


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
    spec.loader.exec_module(mod)
    return mod


bot_mod = _load_bot_module()


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


class ZaloBotInviteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.allowed_file = self.tmp_path / "allowed_chats.json"
        self.log_dir = self.tmp_path / "logs"

        self._orig_allowed_file = getattr(bot_mod, "ALLOWED_CHATS_FILE", None)
        self._orig_log_dir = bot_mod.LOG_DIR
        self._orig_invite_code = getattr(bot_mod, "INVITE_CODE", "")
        self._orig_env_allowed = getattr(bot_mod, "ENV_ALLOWED_CHAT_IDS", set())
        self._orig_saved = getattr(bot_mod, "SAVED_CHAT_IDS", set())
        self._orig_allowed = set(bot_mod.ALLOWED_CHAT_IDS)

        bot_mod.ALLOWED_CHATS_FILE = self.allowed_file
        bot_mod.LOG_DIR = self.log_dir
        bot_mod.INVITE_CODE = "RHM2026"
        bot_mod.ENV_ALLOWED_CHAT_IDS = set()
        bot_mod.SAVED_CHAT_IDS = set()
        bot_mod.ALLOWED_CHAT_IDS = set()
        if hasattr(bot_mod, "_prompted_chats"):
            bot_mod._prompted_chats.clear()
        if hasattr(bot_mod, "_failed_attempts"):
            bot_mod._failed_attempts.clear()

        self.agent_calls: list[str] = []

        def _stub_run_agent(text: str):
            self.agent_calls.append(text)
            return "fake output", {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}, False

        self._run_agent_patch = patch.object(bot_mod, "run_agent", side_effect=_stub_run_agent)
        self._run_agent_patch.start()

    def tearDown(self) -> None:
        self._run_agent_patch.stop()
        if self._orig_allowed_file is not None:
            bot_mod.ALLOWED_CHATS_FILE = self._orig_allowed_file
        bot_mod.LOG_DIR = self._orig_log_dir
        if hasattr(bot_mod, "INVITE_CODE"):
            bot_mod.INVITE_CODE = self._orig_invite_code
        if hasattr(bot_mod, "ENV_ALLOWED_CHAT_IDS"):
            bot_mod.ENV_ALLOWED_CHAT_IDS = self._orig_env_allowed
        if hasattr(bot_mod, "SAVED_CHAT_IDS"):
            bot_mod.SAVED_CHAT_IDS = self._orig_saved
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        self._tmpdir.cleanup()

    def test_doctor_title_formatting(self) -> None:
        cases = [
            ("Nguyễn Bảo Trung", "BS Nguyễn Bảo Trung"),
            ("BS Minh", "BS Minh"),
            ("Bs. Lan", "Bs. Lan"),
            ("Bs.Lan", "Bs.Lan"),
            ("Bác sĩ Hùng", "Bác sĩ Hùng"),
            ("Dr. An", "Dr. An"),
            ("Bson", "BS Bson"),
            ("", "BS"),
            (None, "BS"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(bot_mod._format_doctor_title(raw or ""), expected)

    def test_first_start_unauthorized_prompts_and_does_not_fail_or_log(self) -> None:
        upd = _FakeUpdate("chat_101", "/start", display_name="Nguyễn Bảo Trung")
        ctx = _FakeContext()

        asyncio.run(bot_mod.on_start(upd, ctx))

        self.assertEqual(
            upd.message.replies,
            [
                "Chào BS Nguyễn Bảo Trung ạ, anh/chị nhập mã mời giúp em để bắt đầu dùng "
                "trợ lý AI tra cứu an toàn RHM (chỉ cần nhập 1 lần)."
            ],
        )
        self.assertEqual(self.agent_calls, [])
        self.assertEqual(bot_mod._failed_attempts.get("chat_101", []), [])
        self.assertFalse(self.log_dir.exists())

    def test_first_plain_greeting_unauthorized_prompts_friendly(self) -> None:
        upd = _FakeUpdate("chat_102", "Xin chào", display_name="BS Minh")
        ctx = _FakeContext()

        asyncio.run(bot_mod.on_text(upd, ctx))

        self.assertEqual(
            upd.message.replies,
            [
                "Chào BS Minh ạ, anh/chị nhập mã mời giúp em để bắt đầu dùng "
                "trợ lý AI tra cứu an toàn RHM (chỉ cần nhập 1 lần)."
            ],
        )
        self.assertIn("chat_102", bot_mod._prompted_chats)
        self.assertEqual(self.agent_calls, [])

    def test_activation_via_bare_code_join_and_start_payload(self) -> None:
        # 1) Bare code (case-insensitive + whitespace)
        upd1 = _FakeUpdate("chat_201", "  rhm2026  ", display_name="Nguyễn Bảo Trung")
        asyncio.run(bot_mod.on_text(upd1, _FakeContext()))
        self.assertEqual(len(upd1.message.replies), 1)
        self.assertTrue(
            upd1.message.replies[0].startswith("Đã kích hoạt. Chào BS Nguyễn Bảo Trung ạ!\n")
        )
        self.assertEqual(upd1.message.replies[0], bot_mod.ACTIVATED_TEXT.format(title="BS Nguyễn Bảo Trung"))
        self.assertNotIn(bot_mod.USAGE_TEXT, upd1.message.replies[0])   # bản đủ chỉ in khi /huongdan
        self.assertNotIn("Xin chào!", upd1.message.replies[0])

        # Verify file persistence, schema, no display_name PII, and 0o600 permissions
        self.assertTrue(self.allowed_file.exists())
        data = json.loads(self.allowed_file.read_text(encoding="utf-8"))
        self.assertEqual(data, {"chat_ids": ["chat_201"]})
        self.assertNotIn("Nguyễn Bảo Trung", self.allowed_file.read_text(encoding="utf-8"))
        mode = self.allowed_file.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

        # Reload check
        reloaded = bot_mod._load_saved_chat_ids(self.allowed_file)
        self.assertEqual(reloaded, {"chat_201"})

        # Subsequent clinical text reaches run_agent
        upd1_next = _FakeUpdate("chat_201", "BN uống Sintrom nhổ R48", display_name="Nguyễn Bảo Trung")
        asyncio.run(bot_mod.on_text(upd1_next, _FakeContext()))
        self.assertEqual(self.agent_calls, ["BN uống Sintrom nhổ R48"])
        self.assertEqual(upd1_next.message.replies, ["fake output\n" + bot_mod.FOLLOW_UP_HINT])

        # 2) /join RHM2026
        upd2 = _FakeUpdate("chat_202", "/join RHM2026", display_name="Lan")
        asyncio.run(bot_mod.on_join(upd2, _FakeContext(args=["RHM2026"])))
        self.assertTrue(upd2.message.replies[0].startswith("Đã kích hoạt. Chào BS Lan ạ!"))
        self.assertIn("chat_202", bot_mod.ALLOWED_CHAT_IDS)

        # 3) /start RHM2026
        upd3 = _FakeUpdate("chat_203", "/start RHM2026", display_name="Dr. An")
        asyncio.run(bot_mod.on_start(upd3, _FakeContext(args=["RHM2026"])))
        self.assertTrue(upd3.message.replies[0].startswith("Đã kích hoạt. Chào Dr. An ạ!"))
        self.assertIn("chat_203", bot_mod.ALLOWED_CHAT_IDS)

    def test_already_authorized_calling_join(self) -> None:
        bot_mod.ALLOWED_CHAT_IDS.add("chat_301")
        upd = _FakeUpdate("chat_301", "/join RHM2026", display_name="Hùng")
        asyncio.run(bot_mod.on_join(upd, _FakeContext(args=["RHM2026"])))
        self.assertEqual(
            upd.message.replies,
            ["Tài khoản của anh/chị đã được kích hoạt sẵn rồi ạ. Anh/chị gửi ca ngay được nhé."],
        )
        self.assertEqual(self.agent_calls, [])

    def test_wrong_code_and_bruteforce_throttle_and_recovery(self) -> None:
        chat_id = "chat_401"
        # First /start prompts cleanly (0 failures)
        upd_start = _FakeUpdate(chat_id, "/start", display_name="Hùng")
        asyncio.run(bot_mod.on_start(upd_start, _FakeContext()))

        # 5 wrong attempts within window
        for i in range(5):
            upd_bad = _FakeUpdate(chat_id, f"WRONG{i}", display_name="Hùng")
            asyncio.run(bot_mod.on_text(upd_bad, _FakeContext()))
            self.assertEqual(
                upd_bad.message.replies,
                ["Mã mời chưa đúng ạ. Anh/chị kiểm tra lại và gửi đúng mã mời nhóm đã cung cấp giúp em."],
            )

        # 6th attempt even with valid code is throttled
        upd_throttled = _FakeUpdate(chat_id, "RHM2026", display_name="Hùng")
        asyncio.run(bot_mod.on_text(upd_throttled, _FakeContext()))
        self.assertEqual(
            upd_throttled.message.replies,
            ["Anh/chị đã nhập sai mã mời quá nhiều lần. Anh/chị thử lại sau ít phút giúp em nhé."],
        )
        self.assertNotIn(chat_id, bot_mod.ALLOWED_CHAT_IDS)

        # Advance time past INVITE_WINDOW_SEC (600s) -> valid code works again
        future = bot_mod.time.monotonic() + bot_mod.INVITE_WINDOW_SEC + 5
        with patch.object(bot_mod.time, "monotonic", return_value=future):
            upd_ok = _FakeUpdate(chat_id, "RHM2026", display_name="Hùng")
            asyncio.run(bot_mod.on_text(upd_ok, _FakeContext()))
            self.assertTrue(upd_ok.message.replies[0].startswith("Đã kích hoạt. Chào BS Hùng ạ!"))
            self.assertIn(chat_id, bot_mod.ALLOWED_CHAT_IDS)

    def test_fallback_when_invite_code_empty(self) -> None:
        bot_mod.INVITE_CODE = ""
        upd = _FakeUpdate("chat_501", "/start", display_name="Hùng")
        asyncio.run(bot_mod.on_start(upd, _FakeContext()))
        self.assertEqual(
            upd.message.replies,
            ["Chat id của anh/chị là chat_501. Anh/chị gửi id này cho nhóm để được cấp quyền dùng thử."],
        )

    def test_atomic_save_and_corrupt_json_resilience(self) -> None:
        # Missing file -> empty set
        self.assertEqual(bot_mod._load_saved_chat_ids(self.tmp_path / "missing.json"), set())

        # Corrupt JSON -> empty set (no crash)
        corrupt = self.tmp_path / "corrupt.json"
        corrupt.write_text("{not valid json", encoding="utf-8")
        self.assertEqual(bot_mod._load_saved_chat_ids(corrupt), set())

        # Non-UTF-8 bytes -> empty set (no crash)
        non_utf8 = self.tmp_path / "non_utf8.json"
        non_utf8.write_bytes(b"\xff\xfe\x00\x80")
        self.assertEqual(bot_mod._load_saved_chat_ids(non_utf8), set())

        # Booleans in JSON list are ignored; valid strings/ints kept
        with_bools = self.tmp_path / "with_bools.json"
        with_bools.write_text(
            json.dumps({"chat_ids": [True, False, "chat_ok", 123, ""]}),
            encoding="utf-8",
        )
        self.assertEqual(bot_mod._load_saved_chat_ids(with_bools), {"chat_ok", "123"})

        # Atomic save leaves no .tmp files
        bot_mod._save_chat_ids({"chat_a", "chat_b"}, self.allowed_file)
        leftovers = list(self.tmp_path.glob("*.tmp"))
        self.assertEqual(leftovers, [])
        self.assertEqual(bot_mod._load_saved_chat_ids(self.allowed_file), {"chat_a", "chat_b"})

    def test_group_chat_rejected_for_self_service_invite(self) -> None:
        upd_group = _FakeUpdate("group_901", "RHM2026", display_name="Minh", chat_type="GROUP")
        asyncio.run(bot_mod.on_text(upd_group, _FakeContext()))
        self.assertNotIn("group_901", bot_mod.ALLOWED_CHAT_IDS)
        self.assertFalse(self.allowed_file.exists())
        self.assertEqual(
            upd_group.message.replies,
            [
                "Kích hoạt bằng mã mời chỉ dùng được khi nhắn riêng 1-1 với em. "
                "Anh/chị mở chat riêng với em rồi nhập mã mời giúp em nhé."
            ],
        )

        # Private chat with explicit chat_type="PRIVATE" succeeds
        upd_priv = _FakeUpdate("priv_902", "RHM2026", display_name="Minh", chat_type="PRIVATE")
        asyncio.run(bot_mod.on_text(upd_priv, _FakeContext()))
        self.assertIn("priv_902", bot_mod.ALLOWED_CHAT_IDS)

    def test_help_with_or_without_args_unauthorized_prompts_without_failure(self) -> None:
        for text in ("/help", "/help hướng dẫn", "/help RHM2026"):
            with self.subTest(text=text):
                upd = _FakeUpdate("chat_601", text, display_name="Lan")
                asyncio.run(bot_mod.on_text(upd, _FakeContext()))
                self.assertEqual(
                    upd.message.replies,
                    [
                        "Chào BS Lan ạ, anh/chị nhập mã mời giúp em để bắt đầu dùng "
                        "trợ lý AI tra cứu an toàn RHM (chỉ cần nhập 1 lần)."
                    ],
                )
        self.assertNotIn("chat_601", bot_mod.ALLOWED_CHAT_IDS)
        self.assertEqual(bot_mod._failed_attempts.get("chat_601", []), [])

    def test_unicode_invite_code_and_disk_save_error_resilience(self) -> None:
        bot_mod.INVITE_CODE = "RHM-ĐàNẵng"
        with patch.object(bot_mod, "_save_chat_ids", side_effect=OSError("disk full")):
            upd = _FakeUpdate("chat_701", "rhm-đànẵng", display_name="Tuấn")
            asyncio.run(bot_mod.on_text(upd, _FakeContext()))
            self.assertTrue(upd.message.replies[0].startswith("Đã kích hoạt. Chào BS Tuấn ạ!"))
            self.assertIn("chat_701", bot_mod.ALLOWED_CHAT_IDS)
            self.assertIn("chat_701", bot_mod.SAVED_CHAT_IDS)

    @unittest.skipUnless(_has_real_zalo_bot_sdk(), "requires python-zalo-bot installed")
    def test_script_entrypoint_does_not_shadow_zalo_bot_sdk(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["ZALO_BOT_TOKEN"] = ""
        proc = subprocess.run(
            [sys.executable, "bot/zalo_bot.py"],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotIn("ImportError", proc.stderr)
        self.assertIn("Thiếu ZALO_BOT_TOKEN", proc.stderr)


class ZaloBotCaseFlowTests(unittest.TestCase):
    """Ghép tin bổ sung (design §9), lệnh /moi và ẩn số định danh trước khi gọi model / ghi log."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_log_dir = bot_mod.LOG_DIR
        self._orig_allowed = set(bot_mod.ALLOWED_CHAT_IDS)
        bot_mod.LOG_DIR = Path(self._tmpdir.name) / "logs"
        bot_mod.ALLOWED_CHAT_IDS = {"chat_a", "chat_b"}
        bot_mod._pending.clear()
        bot_mod._last_case.clear()
        self.agent_calls: list[str] = []
        self.needs_more = True

        def _stub_run_agent(text: str):
            self.agent_calls.append(text)
            return "fake output", {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}, self.needs_more

        self._patch = patch.object(bot_mod, "run_agent", side_effect=_stub_run_agent)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        bot_mod._pending.clear()
        bot_mod._last_case.clear()
        self._tmpdir.cleanup()

    def _send(self, chat_id: str, text: str) -> list[str]:
        upd = _FakeUpdate(chat_id, text)
        asyncio.run(bot_mod.on_text(upd, _FakeContext()))
        return upd.message.replies

    def test_follow_up_is_merged_with_pending_case(self) -> None:
        self._send("chat_a", "BN đang uống warfarin. Dự kiến nhổ răng khôn.")
        self.needs_more = False
        replies = self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(
            self.agent_calls[-1],
            "BN đang uống warfarin. Dự kiến nhổ răng khôn.\nBổ sung: Định kê ibuprofen",
        )
        self.assertIn("/moi", replies[-1])
        # Ca đã đủ (needs_more=False) → tin sau không mang dữ kiện cũ.
        self._send("chat_a", "BN uống aspirin, nhổ R38")
        self.assertEqual(self.agent_calls[-1], "BN uống aspirin, nhổ R38")

    def test_pending_is_per_chat_and_expires(self) -> None:
        self._send("chat_a", "BN đang uống warfarin.")
        self._send("chat_b", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")
        text, ts = bot_mod._pending["chat_a"]
        bot_mod._pending["chat_a"] = (text, ts - bot_mod.PENDING_TTL_SEC - 1)
        self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")

    def test_expired_pending_warns_doctor_before_output(self) -> None:
        self._send("chat_a", "BN đang uống warfarin. Dự kiến nhổ răng khôn.")
        text, ts = bot_mod._pending["chat_a"]
        bot_mod._pending["chat_a"] = (text, ts - bot_mod.PENDING_TTL_SEC - 1)
        self.needs_more = False
        replies = self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")
        self.assertTrue(replies[0].startswith(bot_mod.DROPPED_NOTE))
        self.assertNotIn(bot_mod.MERGED_NOTE, replies[-1])
        # Tin sau không có ca chờ → không báo lại.
        replies = self._send("chat_a", "BN uống aspirin, nhổ R38")
        self.assertNotIn(bot_mod.DROPPED_NOTE, "".join(replies))

    def test_expired_pending_warns_even_when_agent_errors(self) -> None:
        self._send("chat_a", "BN đang uống warfarin. Dự kiến nhổ răng khôn.")
        text, ts = bot_mod._pending["chat_a"]
        bot_mod._pending["chat_a"] = (text, ts - bot_mod.PENDING_TTL_SEC - 1)
        with patch.object(bot_mod, "run_agent", side_effect=RuntimeError("api down")):
            replies = self._send("chat_a", "Định kê ibuprofen")
        self.assertTrue(replies[0].startswith(bot_mod.DROPPED_NOTE))
        self.assertIn("hệ thống tra cứu đang lỗi", replies[-1])
        self.assertNotIn("chat_a", bot_mod._pending)

    def test_dropped_note_follows_ttl_constant(self) -> None:
        self.assertIn(f"{bot_mod.PENDING_TTL_SEC // 60} phút", bot_mod.DROPPED_NOTE)

    def test_too_long_pending_is_dropped_with_warning(self) -> None:
        self._send("chat_a", "BN đang uống warfarin. " + "x" * bot_mod.MAX_PENDING_CHARS)
        replies = self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")
        self.assertTrue(replies[0].startswith(bot_mod.DROPPED_NOTE))

    def test_fresh_case_has_no_case_note(self) -> None:
        self.needs_more = False
        replies = "".join(self._send("chat_a", "BN uống aspirin, nhổ R38"))
        self.assertNotIn(bot_mod.DROPPED_NOTE, replies)
        self.assertNotIn(bot_mod.MERGED_NOTE, replies)

    def test_moi_command_clears_pending_without_calling_agent(self) -> None:
        self._send("chat_a", "BN đang uống warfarin.")
        calls = len(self.agent_calls)
        replies = self._send("chat_a", "/moi")
        self.assertEqual(len(self.agent_calls), calls)
        self.assertEqual(replies, ["Đã bắt đầu ca mới."])
        self.assertNotIn("chat_a", bot_mod._pending)
        self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")

    def test_phone_and_id_numbers_are_masked_before_agent_and_log(self) -> None:
        self.needs_more = False
        replies = self._send("chat_a", "BN SĐT 0912 345 678, CCCD 001203004567, uống aspirin. Nhổ R38")
        sent = self.agent_calls[-1]
        self.assertNotIn("0912", sent)
        self.assertNotIn("001203004567", sent)
        self.assertIn("nhổ r38", sent.lower())
        self.assertTrue(replies[0].startswith("⚠️"))
        log_text = "".join(p.read_text(encoding="utf-8") for p in bot_mod.LOG_DIR.glob("*.jsonl"))
        self.assertNotIn("0912", log_text)
        self.assertNotIn("001203004567", log_text)

    def test_thanks_while_case_pending_is_not_merged(self) -> None:
        # "cảm ơn" từng bị ghép "…\nBổ sung: cảm ơn" → bot gửi lại nguyên ca và câu "Em đã ghép với tin trước".
        self._send("chat_a", "BN đang uống warfarin. Dự kiến nhổ răng khôn.")
        calls = len(self.agent_calls)
        replies = self._send("chat_a", "Dạ em cảm ơn nhiều ạ")
        self.assertEqual(len(self.agent_calls), calls)
        self.assertTrue(replies[-1].startswith("Dạ không có gì"))
        self.assertNotIn("/moi", replies[-1])
        # Ca đang chờ vẫn còn: tin bổ sung thật vẫn được ghép.
        self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1],
                         "BN đang uống warfarin. Dự kiến nhổ răng khôn.\nBổ sung: Định kê ibuprofen")

    def test_photo_or_sticker_gets_type_it_reply_without_agent(self) -> None:
        upd = _FakeUpdate("chat_a", "")
        upd.message.text = None
        upd.message.photo_url = "https://example.invalid/don.jpg"
        asyncio.run(bot_mod.on_non_text(upd, _FakeContext()))
        self.assertEqual(self.agent_calls, [])
        self.assertIn("ảnh", upd.message.replies[-1])
        self.assertIn("gõ", upd.message.replies[-1])
        # Chat chưa kích hoạt: không trả lời gì (không lộ bot cho người lạ).
        upd2 = _FakeUpdate("chat_x", "")
        upd2.message.text = None
        asyncio.run(bot_mod.on_non_text(upd2, _FakeContext()))
        self.assertEqual(upd2.message.replies, [])

    def test_follow_up_with_them_after_finished_case_is_merged(self) -> None:
        self.needs_more = False
        replies = self._send("chat_a", "BN uống warfarin. Nhổ R48, kê Augmentin")
        self.assertIn("thêm", replies[-1])                     # gợi ý cách hỏi tiếp
        self._send("chat_a", "thêm paracetamol được không")
        self.assertEqual(self.agent_calls[-1],
                         "BN uống warfarin. Nhổ R48, kê Augmentin\nBổ sung: thêm paracetamol được không")
        # Tin không mở đầu bằng "thêm"/"bổ sung" là ca mới.
        self._send("chat_a", "BN uống aspirin, nhổ R38")
        self.assertEqual(self.agent_calls[-1], "BN uống aspirin, nhổ R38")

    def test_moi_also_forgets_finished_case(self) -> None:
        self.needs_more = False
        self._send("chat_a", "BN uống warfarin. Nhổ R48, kê Augmentin")
        self._send("chat_a", "/moi")
        self._send("chat_a", "thêm paracetamol")
        self.assertEqual(self.agent_calls[-1], "thêm paracetamol")

    def test_clinical_numbers_are_not_masked(self) -> None:
        text = "BN INR 2.5, HbA1c 7.2%, aspirin 81mg. Nhổ R48"
        self.assertEqual(bot_mod.mask_identifiers(text), (text, False))


class ZaloBotCommunicationTests(unittest.TestCase):
    """Kế hoạch giao tiếp Trung duyệt 28/11 (A–F): tin kích hoạt ngắn + /huongdan, chào lại ngắn trong 12 giờ,
    hỏi lại tăng dần, /sai, bản tin gọn 🟡 + "chi tiết"."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_log_dir = bot_mod.LOG_DIR
        self._orig_allowed = set(bot_mod.ALLOWED_CHAT_IDS)
        bot_mod.LOG_DIR = Path(self._tmpdir.name) / "logs"
        bot_mod.ALLOWED_CHAT_IDS = {"chat_a"}
        for store in (bot_mod._pending, bot_mod._last_case, bot_mod._last_greet, bot_mod._misses):
            store.clear()
        self.calls: list[tuple[str, bool]] = []
        self.output = "fake output"
        self.needs_more = False

        def _stub_run_agent(text: str, detail: bool = False):
            self.calls.append((text, detail))
            out = "full output" if detail else self.output
            return out, {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}, self.needs_more

        self._patch = patch.object(bot_mod, "run_agent", side_effect=_stub_run_agent)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        for store in (bot_mod._pending, bot_mod._last_case, bot_mod._last_greet, bot_mod._misses):
            store.clear()
        self._tmpdir.cleanup()

    def _send(self, text: str, chat_id: str = "chat_a") -> list[str]:
        upd = _FakeUpdate(chat_id, text)
        asyncio.run(bot_mod.on_text(upd, _FakeContext()))
        return upd.message.replies

    def _log_records(self) -> list[dict]:
        return [json.loads(line) for f in sorted(bot_mod.LOG_DIR.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines()]

    # A
    def test_activation_text_is_short_and_says_ai(self) -> None:
        text = bot_mod.ACTIVATED_TEXT.format(title="BS Lan")
        self.assertLessEqual(len(text.splitlines()), 8)
        for must in ("trợ lý AI", "BS là người quyết định", "ẩn danh", "Ví dụ:", "/huongdan"):
            self.assertIn(must, text)

    def test_huongdan_prints_full_usage_in_em_voice(self) -> None:
        replies = self._send("/huongdan")
        self.assertEqual(replies, [bot_mod.USAGE_TEXT])
        self.assertEqual(self.calls, [])
        self.assertNotRegex(bot_mod.USAGE_TEXT, r"\bBot\b|\bbot sẽ\b")
        for cmd in ("/moi", "thêm", "chi tiết", "/sai"):
            self.assertIn(cmd, bot_mod.USAGE_TEXT)

    # B
    def test_second_greeting_within_12h_is_short(self) -> None:
        first = self._send("hi")
        self.assertIn("Ví dụ:", first[-1])
        second = self._send("chào em")
        self.assertEqual(second, [bot_mod.AGENT_TEXT["HELLO_AGAIN"]])
        bot_mod._last_greet["chat_a"] -= bot_mod.GREET_AGAIN_SEC + 1
        third = self._send("hello")
        self.assertIn("Ví dụ:", third[-1])
        self.assertEqual(self.calls, [])

    def test_help_question_always_gets_full_intro(self) -> None:
        self._send("hi")
        replies = self._send("em làm được gì")
        self.assertIn("Ví dụ:", replies[-1])

    def test_bye_gets_goodbye(self) -> None:
        self.assertEqual(self._send("tạm biệt em"), [bot_mod.AGENT_TEXT["BYE"]])

    # C
    def test_second_message_without_entities_gets_template(self) -> None:
        q1 = bot_mod.AGENT_TEXT["Q1"]
        self.output = q1 + "\n" + bot_mod.AGENT_TEXT["FOOTER"]
        self.needs_more = True
        first = self._send("abc")
        self.assertIn(q1, first[-1])
        second = self._send("xyz")
        self.assertIn(bot_mod.AGENT_TEXT["REPAIR"], second[-1])
        self.assertNotIn(q1, second[-1])
        # Ca nhận ra thực thể → đếm lại từ đầu.
        self.output, self.needs_more = "🔴 Nguy cơ cao:\n- [DDI-001] x. Nguồn: y.", False
        self._send("BN uống warfarin, kê ibuprofen")
        self.output, self.needs_more = q1 + "\n" + bot_mod.AGENT_TEXT["FOOTER"], True
        again = self._send("abc")
        self.assertIn(q1, again[-1])

    # D
    def test_sai_feedback_is_logged_without_agent(self) -> None:
        self._send("BN uống warfarin, kê ibuprofen")
        calls = len(self.calls)
        replies = self._send("/sai DDI-029 thừa, SĐT 0912 345 678")
        self.assertEqual(replies, [bot_mod.FEEDBACK_ACK])
        self.assertEqual(len(self.calls), calls)
        rec = self._log_records()[-1]
        self.assertEqual(rec["kind"], "feedback")
        self.assertNotIn("0912", rec["input"])
        self.assertIn("chat_a", bot_mod._last_case)          # không đụng ca vừa xong

    def test_sai_from_unknown_chat_gets_invite_flow(self) -> None:
        bot_mod.ALLOWED_CHAT_IDS = set()
        with patch.object(bot_mod, "INVITE_CODE", "RHM2026"):
            replies = self._send("/sai abc", chat_id="chat_z")
        self.assertIn("mã mời", replies[-1])
        self.assertFalse(bot_mod.LOG_DIR.exists())

    # F
    def test_moderate_reply_offers_detail_and_detail_reruns_case(self) -> None:
        self.output = "Em rà xong rồi ạ — có 1 cần thận trọng.\n🟡 Cần thận trọng:\n- [DDI-029] a. Nguồn: b."
        replies = self._send("BN uống warfarin, kê paracetamol")
        self.assertIn(bot_mod.DETAIL_HINT, replies[-1])
        detail = self._send("chi tiết")
        self.assertEqual(self.calls[-1], ("BN uống warfarin, kê paracetamol", True))
        self.assertEqual(detail, ["full output"])
        self.assertIn("chat_a", bot_mod._last_case)
        self.assertEqual(self._log_records()[-1]["kind"], "detail")

    def test_no_moderate_no_detail_hint(self) -> None:
        self.output = "🔴 Nguy cơ cao:\n- [DDI-001] a. Nguồn: b."
        self.assertNotIn(bot_mod.DETAIL_HINT, self._send("BN uống warfarin, kê ibuprofen")[-1])

    def test_detail_without_recent_case(self) -> None:
        self.assertEqual(self._send("xem chi tiet"), [bot_mod.NO_DETAIL_TEXT])
        self.assertEqual(self.calls, [])

    def test_detail_uses_pending_case_without_merging(self) -> None:
        self.output = "🟡 Cần thận trọng nếu dùng cùng nhau:\n- [DDI-029] a. Nguồn: b."
        self.needs_more = True
        self._send("paracetamol, warfarin")
        self._send("chi tiết")
        self.assertEqual(self.calls[-1], ("paracetamol, warfarin", True))
        self.assertEqual(bot_mod._pending["chat_a"][0], "paracetamol, warfarin")

    def test_log_stats_feedback_text_matches_bot(self) -> None:
        spec = importlib.util.spec_from_file_location("log_stats", Path(__file__).resolve().parent / "log_stats.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.FEEDBACK_ACK, bot_mod.FEEDBACK_ACK)

    def test_log_kind_marks_small_talk_and_case(self) -> None:
        self._send("cảm ơn em")
        self._send("BN uống warfarin, kê ibuprofen")
        kinds = [r["kind"] for r in self._log_records()]
        self.assertEqual(kinds, ["small_talk", "case"])


class ZaloBotLogPrivacyTests(unittest.TestCase):
    """Log bot không được giữ thông tin định danh BN (spec.md dòng nói về log bot · docs/cp4-agent-plan.md mục 2)."""

    CLINICAL = "BN 65t uống Sintrom, ĐTĐ. Dự kiến nhổ R48. Định kê Augmentin 625mg"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._orig_log_dir = bot_mod.LOG_DIR
        bot_mod.LOG_DIR = Path(self.tmp.name) / "logs"

    def tearDown(self) -> None:
        bot_mod.LOG_DIR = self._orig_log_dir
        self.tmp.cleanup()

    def _records(self) -> list[dict]:
        files = sorted(bot_mod.LOG_DIR.glob("*.jsonl"))
        return [json.loads(line) for f in files for line in f.read_text(encoding="utf-8").splitlines()]

    def test_mask_pii_hides_identifiers_and_keeps_clinical_text(self) -> None:
        text = (self.CLINICAL + ". SĐT 0912 345 678, +84 912.345.679, CCCD 001203004005, "
                "email bn.test@example.com, mã hồ sơ: HS-2026-0042, thẻ BHYT DN4797915123456")
        masked = bot_mod.mask_pii(text)
        for secret in ("0912 345 678", "912.345.679", "001203004005", "bn.test@example.com",
                       "HS-2026-0042", "DN4797915123456"):
            self.assertNotIn(secret, masked)
        self.assertIn(self.CLINICAL, masked)

    def test_mask_pii_record_code_after_bn_label(self) -> None:
        # Câu B20 của eval/benchmark.csv: "BN" đứng giữa nhãn và mã, không được coi "BN" là mã.
        masked = bot_mod.mask_pii("Mã hồ sơ BN: TEST-HS-000. BN đang dùng warfarin")
        self.assertNotIn("TEST-HS-000", masked)
        self.assertIn("BN đang dùng warfarin", masked)

    def test_log_turn_masks_input_output_and_error(self) -> None:
        bot_mod.log_turn(chat_id="c1", user_input="BN SĐT 0912345678 uống Sintrom",
                         output="Đã đối chiếu — Sintrom (0912345678)", summary={},
                         error="RuntimeError: echo 0912345678")
        rec = self._records()[0]
        blob = json.dumps(rec, ensure_ascii=False)
        self.assertNotIn("0912345678", blob)
        self.assertIn("Sintrom", rec["input"])
        self.assertFalse(rec["pii_dropped"])

    def test_on_text_drops_input_when_agent_flags_pii(self) -> None:
        flagged = bot_mod.PII_WARNING + "\nĐã đối chiếu — Thuốc đang dùng: Sintrom"
        bot_mod.ALLOWED_CHAT_IDS.add("chat-pii")
        try:
            with patch.object(bot_mod, "run_agent", return_value=(flagged, {}, False)):
                update = _FakeUpdate("chat-pii", "BN Nguyễn Văn Test 65t uống Sintrom")
                asyncio.run(bot_mod.on_text(update, _FakeContext()))
        finally:
            bot_mod.ALLOWED_CHAT_IDS.discard("chat-pii")
        rec = self._records()[0]
        self.assertNotIn("Nguyễn Văn Test", json.dumps(rec, ensure_ascii=False))
        self.assertTrue(rec["pii_dropped"])
        self.assertEqual(update.message.replies, [flagged + "\n" + bot_mod.FOLLOW_UP_HINT])


class _FlakyMessage(_FakeMessage):
    """reply_text lỗi `fails` lần đầu rồi mới gửi được (mô phỏng lỗi mạng / giới hạn tốc độ của Zalo)."""

    def __init__(self, chat_id: str, text: str, fails: int):
        super().__init__(chat_id, text)
        self.fails = fails
        self.attempts = 0

    async def reply_text(self, chunk: str) -> None:
        self.attempts += 1
        if self.attempts <= self.fails:
            raise RuntimeError("network down")
        self.replies.append(chunk)


class ZaloBotDeliveryTests(unittest.TestCase):
    """Issue #32 (miss tin): gửi lỗi thì thử lại; lỗi bất ngờ trong handler không được tắt vòng polling."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_log_dir = bot_mod.LOG_DIR
        self._orig_allowed = set(bot_mod.ALLOWED_CHAT_IDS)
        bot_mod.LOG_DIR = Path(self._tmpdir.name) / "logs"
        bot_mod.ALLOWED_CHAT_IDS = {"chat_a"}
        bot_mod._pending.clear()
        bot_mod._last_case.clear()
        self._patches = [
            patch.object(bot_mod, "run_agent", return_value=("fake output", {"models": ["fake"]}, False)),
            patch.object(bot_mod, "SEND_RETRY_SEC", 0, create=True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        bot_mod._pending.clear()
        bot_mod._last_case.clear()
        self._tmpdir.cleanup()

    def _log_records(self) -> list[dict]:
        return [json.loads(line) for f in sorted(bot_mod.LOG_DIR.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines()]

    def test_send_failure_is_retried(self) -> None:
        upd = _FakeUpdate("chat_a", "x")
        upd.message = _FlakyMessage("chat_a", "x", fails=1)
        asyncio.run(bot_mod._reply_chunks(upd, "Em rà xong rồi ạ."))
        self.assertEqual(upd.message.replies, ["Em rà xong rồi ạ."])

    def test_send_failure_after_retries_is_logged(self) -> None:
        upd = _FakeUpdate("chat_a", "x")
        upd.message = _FlakyMessage("chat_a", "x", fails=99)
        asyncio.run(bot_mod._reply_chunks(upd, "Em rà xong rồi ạ."))
        self.assertEqual(upd.message.replies, [])
        self.assertEqual(upd.message.attempts, bot_mod.SEND_ATTEMPTS)
        rec = self._log_records()[-1]
        self.assertEqual(rec["kind"], "send_error")
        self.assertIn("RuntimeError", rec["error"])

    def test_unexpected_error_in_on_text_does_not_escape_and_doctor_is_told(self) -> None:
        upd = _FakeUpdate("chat_a", "BN uống warfarin, nhổ R48")
        with patch.object(bot_mod, "mask_identifiers", side_effect=ValueError("boom")):
            asyncio.run(bot_mod.on_text(upd, _FakeContext()))   # không được ném lỗi ra vòng polling
        self.assertEqual(upd.message.replies, [bot_mod.ERROR_TEXT])
        self.assertEqual(self._log_records()[-1]["kind"], "handler_error")

    def test_every_registered_handler_is_guarded(self) -> None:
        for fn in (bot_mod.on_start, bot_mod.on_join, bot_mod.on_new_case, bot_mod.on_usage,
                   bot_mod.on_feedback, bot_mod.on_non_text, bot_mod.on_text):
            self.assertTrue(getattr(fn, "_guarded", False), fn.__name__)


if __name__ == "__main__":
    unittest.main()
