"""Test bot/zalo_bot.py: mã mời và lưu chat_id, lời chào BS, ghép tin bổ sung (design §9), ẩn số định danh."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from bot._testkit import (  # noqa: F401
    bot_mod, Alert, Reply, reply_mod, _text_reply, HIGH_ALERT, MODERATE_ALERT, _has_real_zalo_bot_sdk, _FakeUser, _FakeChat, _FakeMessage, _FakeUpdate, _FakeBot, _FakeContext,
)


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
            return _text_reply(), {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}

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

    def _log_records(self) -> list[dict]:
        if not self.log_dir.exists():
            return []
        return [json.loads(line) for f in sorted(self.log_dir.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_unauthorized_steps_are_logged_without_text_or_name(self) -> None:
        """Người chưa có mã: mỗi bước ghi 1 dòng kind="invite" (chỉ kết quả), không ghi chữ đã gõ hay tên."""
        ctx = _FakeContext()
        asyncio.run(bot_mod.on_text(_FakeUpdate("chat_301", "BN uống warfarin 0912345678", display_name="Lan"), ctx))
        asyncio.run(bot_mod.on_text(_FakeUpdate("chat_301", "SAIMA99", display_name="Lan"), ctx))
        asyncio.run(bot_mod.on_text(_FakeUpdate("chat_301", "rhm2026", display_name="Lan"), ctx))
        sticker = _FakeUpdate("chat_302", "", display_name="Hùng")
        sticker.message.text = None
        asyncio.run(bot_mod.on_non_text(sticker, ctx))
        recs = self._log_records()
        self.assertEqual([(r["kind"], r["input"]) for r in recs], [
            ("invite", "[invite] prompt"), ("invite", "[invite] wrong"),
            ("invite", "[invite] activated"), ("invite", "[invite] non_text"),
        ])
        raw = "".join(json.dumps(r, ensure_ascii=False) for r in recs)
        for secret in ("warfarin", "0912345678", "SAIMA99", "rhm2026", "RHM2026", "Lan", "Hùng", "chat_301"):
            self.assertNotIn(secret, raw)
        self.assertEqual({r["output"] for r in recs}, {""})
        self.assertEqual(self.agent_calls, [])

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
        self.assertEqual([r["input"] for r in self._log_records()], ["[invite] prompt"])   # chỉ ghi kết quả

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
        bot_mod._conversations.clear()
        self.agent_calls: list[str] = []
        self.needs_more = True

        def _stub_run_agent(text: str):
            self.agent_calls.append(text)
            return _text_reply(needs_more=self.needs_more), {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}

        self._patch = patch.object(bot_mod, "run_agent", side_effect=_stub_run_agent)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        bot_mod._conversations.clear()
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
        bot_mod._conv("chat_a").case.at -= bot_mod.PENDING_TTL_SEC + 1
        self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")

    def test_expired_pending_warns_doctor_before_output(self) -> None:
        self._send("chat_a", "BN đang uống warfarin. Dự kiến nhổ răng khôn.")
        bot_mod._conv("chat_a").case.at -= bot_mod.PENDING_TTL_SEC + 1
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
        bot_mod._conv("chat_a").case.at -= bot_mod.PENDING_TTL_SEC + 1
        with patch.object(bot_mod, "run_agent", side_effect=RuntimeError("api down")):
            replies = self._send("chat_a", "Định kê ibuprofen")
        self.assertTrue(replies[0].startswith(bot_mod.DROPPED_NOTE))
        self.assertIn("hệ thống tra cứu đang lỗi", replies[-1])
        self.assertIsNone(bot_mod._conv("chat_a").case)

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
        self.assertEqual(replies, [bot_mod.NEW_CASE_TEXT])
        self.assertIsNone(bot_mod._conv("chat_a").case)
        self._send("chat_a", "Định kê ibuprofen")
        self.assertEqual(self.agent_calls[-1], "Định kê ibuprofen")

    def test_moi_is_logged_as_case_boundary(self) -> None:
        # Log VM 28/11 08:30–08:34: không biết tin nào tách ca vì /moi không có dòng log.
        self._send("chat_a", "BN đang uống warfarin.")
        self._send("chat_a", "/moi")
        recs = [json.loads(line) for f in bot_mod.LOG_DIR.glob("*.jsonl")
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual((recs[-1]["kind"], recs[-1]["input"], recs[-1]["output"]),
                         ("new_case", "/moi", bot_mod.NEW_CASE_TEXT))
        self.assertEqual(recs[-1]["tokens_in"], 0)
        # Lệnh tới qua on_text (SDK có lúc giao lệnh cho on_text) cũng chỉ một dòng.
        self._send("chat_a", "/moi")
        recs2 = [json.loads(line) for f in bot_mod.LOG_DIR.glob("*.jsonl")
                 for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(recs2), len(recs) + 1)
        # Chat chưa có quyền: không ghi dòng new_case.
        self._send("chat_x", "/moi")
        recs3 = [json.loads(line) for f in bot_mod.LOG_DIR.glob("*.jsonl")
                 for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertFalse([r for r in recs3[len(recs2):] if r["kind"] == "new_case"])

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
        recs = [json.loads(line) for f in bot_mod.LOG_DIR.glob("*.jsonl")
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(recs[-1]["kind"], "non_text")   # BS đã kích hoạt gửi ảnh: có dòng log
        self.assertNotIn("example.invalid", json.dumps(recs, ensure_ascii=False))
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

    def test_them_new_patient_is_not_merged(self) -> None:
        # Review PR #30 (Nguyên): "Thêm 1 ca: …", "Thêm BN nữa …" là BN khác — không ghép vào ca trước / ca đang chờ.
        for needs_more in (False, True):
            for text in ("Thêm 1 ca: BN uống aspirin, nhổ R38", "Thêm BN nữa uống warfarin, nhổ R48",
                         "thêm ca mới: BN có thai, kê ibuprofen", "Bổ sung 1 bệnh nhân: BN uống Sintrom",
                         "Thêm ca: BN 30t kê Augmentin", "thêm một bệnh nhân uống clopidogrel"):
                with self.subTest(needs_more=needs_more, text=text):
                    self.needs_more = needs_more
                    self._send("chat_a", "/moi")
                    self._send("chat_a", "BN uống warfarin. Nhổ R48, kê Augmentin")
                    self._send("chat_a", text)
                    self.assertEqual(self.agent_calls[-1], text)
        # Vẫn là bổ sung cho cùng BN: ghép như cũ.
        for text in ("thêm cả paracetamol", "thêm BN dị ứng penicillin", "thêm: BN có dị ứng penicillin",
                     "Bổ sung ca này: BN tiểu đường", "bổ sung BN có uống aspirin"):
            with self.subTest(text=text):
                self.needs_more = False
                self._send("chat_a", "/moi")
                self._send("chat_a", "BN uống warfarin. Nhổ R48, kê Augmentin")
                self._send("chat_a", text)
                self.assertEqual(self.agent_calls[-1], "BN uống warfarin. Nhổ R48, kê Augmentin\nBổ sung: " + text)

    def test_new_patient_description_is_not_merged_into_pending_case(self) -> None:
        # Log VM 28/11 15:35: ca BN mang thai đang chờ, BS gửi "giờ bệnh nhân không có bệnh lý gì, nhổ răng kê augmentin…"
        # → bot ghép, vẫn ghi "Bệnh nền: Đang mang thai". Tin tả BN (giới / tuổi) hoặc phủ nhận nhóm mà ca chờ đã có
        # là BN khác: không ghép, báo BS cách ghép nếu cùng BN.
        pending = Reply(checked=[("Bệnh nền", "Đang mang thai / Thai kỳ"), ("Dị ứng", "không khai")], needs_more=True)

        def _stub(text: str):
            self.agent_calls.append(text)
            return pending, {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}

        with patch.object(bot_mod, "run_agent", side_effect=_stub):
            for text in ("giờ bệnh nhân không có bệnh lý gì, nhổ răng kê augmentin và paracetamol nhé",
                         "BN nam 58 tuổi, uống warfarin, nhổ R48", "Bệnh nhân nữ, nhổ R38 kê ibuprofen"):
                with self.subTest(text=text):
                    self._send("chat_a", "/moi")
                    self._send("chat_a", "bệnh nhân nữ đang mang thai kê thuốc gì được nhỉ")
                    replies = self._send("chat_a", text)
                    self.assertEqual(self.agent_calls[-1], text)
                    self.assertIn(bot_mod.SPLIT_NOTE, replies[-1])
                    self.assertNotIn(bot_mod.MERGED_NOTE, replies[-1])
            # Trả lời câu bot hỏi, kể cả phủ nhận nhóm ca chờ CHƯA có, vẫn ghép.
            for text in ("dùng aspirin", "không dị ứng thuốc", "nhổ răng, kê augmentin", "thêm BN 30 tuổi"):
                with self.subTest(text=text):
                    self._send("chat_a", "/moi")
                    self._send("chat_a", "bệnh nhân nữ đang mang thai kê thuốc gì được nhỉ")
                    self._send("chat_a", text)
                    self.assertEqual(self.agent_calls[-1],
                                     "bệnh nhân nữ đang mang thai kê thuốc gì được nhỉ\nBổ sung: " + text)

    def test_emergency_only_reply_has_no_follow_up_hint(self) -> None:
        # Log VM 28/11 15:30: tin chỉ báo cấp cứu → agent trả riêng dòng cấp cứu (footer=False); không mời "thêm …".
        line = "🚫 Em không hỗ trợ xử trí cấp cứu. Anh/chị xử trí theo phác đồ cấp cứu của cơ sở, cần thì gọi 115."
        text = bot_mod.compose_reply(Reply(head=[line], footer=False), repeat_miss=False, case_status="new", had_ids=False)
        self.assertEqual(text, line)

    def test_merged_follow_up_mentions_moi_once(self) -> None:
        # Review #30 (Nguyên) ý 5: MERGED_NOTE và FOLLOW_UP_HINT cùng nhắc /moi làm tin dài.
        self.needs_more = False
        self._send("chat_a", "BN uống warfarin. Nhổ R48")
        replies = self._send("chat_a", "thêm ibuprofen")
        self.assertEqual(replies[-1].count("/moi"), 1, replies[-1])

    def test_on_text_sends_formatted_reply(self) -> None:
        self.needs_more = False
        checked = Reply(checked=[("Bệnh nền", "không khai"), ("Thuốc đang dùng", "Warfarin")])
        with patch.object(bot_mod, "run_agent", return_value=(checked, {})):
            replies = self._send("chat_a", "BN uống warfarin")
        self.assertIn("• Chưa khai: bệnh nền", replies[-1])

    def test_moi_also_forgets_finished_case(self) -> None:
        self.needs_more = False
        self._send("chat_a", "BN uống warfarin. Nhổ R48, kê Augmentin")
        self._send("chat_a", "/moi")
        self._send("chat_a", "thêm paracetamol")
        self.assertEqual(self.agent_calls[-1], "thêm paracetamol")

    def test_clinical_numbers_are_not_masked(self) -> None:
        text = "BN INR 2.5, HbA1c 7.2%, aspirin 81mg. Nhổ R48"
        self.assertEqual(bot_mod.mask_identifiers(text), (text, False))


class ZaloBotConcurrencyTests(unittest.TestCase):
    """Nhiều BS nhắn cùng lúc: chat khác nhau chạy song song, cùng chat giữ thứ tự, trace không lẫn."""

    def test_parallel_run_agent_keeps_separate_traces(self) -> None:
        import threading
        barrier = threading.Barrier(2)

        @bot_mod.tracing.model_call
        def fake_model(tag: str) -> dict:
            barrier.wait(timeout=5)   # ép 2 ca chồng lên nhau trong lúc đang ghi trace
            return {"text": tag, "model": "fake", "tokens_in": 1, "tokens_out": 1}

        def fake_answer(text: str) -> dict:
            fake_model(text)
            return {"reply": _text_reply(text)}

        async def go():
            return await asyncio.gather(asyncio.to_thread(bot_mod.run_agent, "a"),
                                        asyncio.to_thread(bot_mod.run_agent, "b"))

        with patch.object(bot_mod, "answer", side_effect=fake_answer):
            results = asyncio.run(go())
        self.assertEqual([r[1]["model_calls"] for r in results], [1, 1])

    def test_dispatch_parallel_across_chats_ordered_within_chat(self) -> None:
        events: list[tuple[str, str, str]] = []

        class _App:
            async def process_update(self, update) -> None:
                events.append(("start", update.message.chat.id, update.message.text))
                await asyncio.sleep(0.2)
                events.append(("end", update.message.chat.id, update.message.text))

        async def go():
            app = _App()
            t0 = time.monotonic()
            for chat, text in (("A", "1"), ("A", "2"), ("B", "1")):
                bot_mod._spawn_update(app, _FakeUpdate(chat, text))
            await asyncio.gather(*list(bot_mod._inflight))
            return time.monotonic() - t0

        elapsed = asyncio.run(go())
        self.assertLess(elapsed, 0.55)   # A1→A2 nối tiếp (0.4s), B chạy song song; tuần tự sẽ là 0.6s
        a = [(k, t) for k, c, t in events if c == "A"]
        self.assertEqual(a, [("start", "1"), ("end", "1"), ("start", "2"), ("end", "2")])
        self.assertLess(events.index(("start", "B", "1")), events.index(("end", "A", "1")))

    def test_third_message_waits_after_lock_handoff(self) -> None:
        """Tin 3 cùng chat tới đúng lúc tin 1 vừa nhả khoá cho tin 2: không được chạy chồng tin 2."""
        overlaps: list[tuple[str, set[str]]] = []
        running: set[str] = set()

        class _App:
            async def process_update(self, update) -> None:
                text = update.message.text
                if running:
                    overlaps.append((text, set(running)))
                running.add(text)
                await asyncio.sleep(0.1)
                running.discard(text)

        async def go():
            app = _App()
            bot_mod._spawn_update(app, _FakeUpdate("A", "1"))
            bot_mod._spawn_update(app, _FakeUpdate("A", "2"))
            await asyncio.sleep(0.12)   # tin 1 xong, tin 2 đang giữ khoá
            bot_mod._spawn_update(app, _FakeUpdate("A", "3"))
            await asyncio.gather(*list(bot_mod._inflight))

        asyncio.run(go())
        self.assertEqual(overlaps, [])


if __name__ == "__main__":
    unittest.main()
