"""Test bot/zalo_bot.py: kế hoạch giao tiếp (chào lại, hỏi lại tăng dần, /sai, "chi tiết"), log không giữ định danh, gửi lại khi lỗi và handler không làm dừng polling (issue #32)."""
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


class ZaloBotCommunicationTests(unittest.TestCase):
    """Kế hoạch giao tiếp Trung duyệt 28/11 (A–F): tin kích hoạt ngắn + /huongdan, chào lại ngắn trong 12 giờ,
    hỏi lại tăng dần, /sai, bản tin gọn 🟡 + "chi tiết"."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_log_dir = bot_mod.LOG_DIR
        self._orig_allowed = set(bot_mod.ALLOWED_CHAT_IDS)
        bot_mod.LOG_DIR = Path(self._tmpdir.name) / "logs"
        bot_mod.ALLOWED_CHAT_IDS = {"chat_a"}
        bot_mod._conversations.clear()
        self.calls: list[str] = []
        self.reply = _text_reply()

        def _stub_run_agent(text: str):
            self.calls.append(text)
            return self.reply, {"models": ["fake"], "tokens_in": 1, "tokens_out": 2}

        self._patch = patch.object(bot_mod, "run_agent", side_effect=_stub_run_agent)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        bot_mod._conversations.clear()
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
        bot_mod._conv("chat_a").greeted_at -= bot_mod.GREET_AGAIN_SEC + 1
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
        self.reply = Reply(question=q1, question_key="Q1", needs_more=True)
        first = self._send("abc")
        self.assertIn(q1, first[-1])
        second = self._send("xyz")
        self.assertIn(bot_mod.AGENT_TEXT["REPAIR"], second[-1])
        self.assertNotIn(q1, second[-1])
        # Ca nhận ra thực thể → đếm lại từ đầu.
        self.reply = Reply(alerts=[HIGH_ALERT])
        self._send("BN uống warfarin, kê ibuprofen")
        self.reply = Reply(question=q1, question_key="Q1", needs_more=True)
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
        self.assertIsNotNone(bot_mod._conv("chat_a").case)   # không đụng ca vừa xong

    def test_sai_from_unknown_chat_gets_invite_flow(self) -> None:
        bot_mod.ALLOWED_CHAT_IDS = set()
        with patch.object(bot_mod, "INVITE_CODE", "RHM2026"):
            replies = self._send("/sai abc", chat_id="chat_z")
        self.assertIn("mã mời", replies[-1])
        recs = self._log_records()   # không ghi góp ý của chat lạ; chỉ ghi bước mã mời, không ghi chữ đã gõ
        self.assertEqual([(r["kind"], r["input"]) for r in recs], [("invite", "[invite] prompt")])

    # F
    FULL = Reply(verdict="Em rà xong rồi ạ — có 1 nguy cơ cao, 1 cần thận trọng.", alerts=[HIGH_ALERT, MODERATE_ALERT],
                 checked=[("Bệnh nền", "không khai"), ("Thuốc đang dùng", "Warfarin (kháng vitamin K)")])

    def test_moderate_reply_offers_detail_and_detail_reuses_case(self) -> None:
        self.reply = Reply(alerts=[MODERATE_ALERT])
        replies = self._send("BN uống warfarin, kê paracetamol")
        self.assertIn(reply_mod.DETAIL_HINT, replies[-1])
        detail = self._send("chi tiết")
        self.assertEqual(self.calls, ["BN uống warfarin, kê paracetamol"])   # "chi tiết" không gọi lại agent
        self.assertEqual(detail, [reply_mod.render_detail(self.reply)])
        self.assertIsNotNone(bot_mod._conv("chat_a").case)
        self.assertEqual(self._log_records()[-1]["kind"], "detail")

    def test_first_reply_is_short_without_sources(self) -> None:
        # Trung duyệt 28/11: tin đầu gọn (mã, cặp, hướng xử trí 🔴 giữ nguyên), nguồn đầy đủ để ở "chi tiết".
        self.reply = self.FULL
        reply = "\n".join(self._send("BN uống warfarin, kê Alaxan"))
        self.assertNotIn("Nguồn:", reply)
        self.assertIn("- [DDI-001] Ibuprofen + Warfarin → Tránh phối hợp, theo dõi INR.", reply)
        self.assertIn("- [DDI-029] Paracetamol + Warfarin\n", reply)   # 🟡 gọn: chỉ mã + cặp, nguy cơ ở "chi tiết"
        self.assertNotIn("tăng INR", reply)
        for keep in ("Em rà xong", "📋 Em đã đối chiếu:", "Warfarin (kháng vitamin K)", bot_mod.AGENT_TEXT["FOOTER"],
                     reply_mod.DETAIL_HINT):
            self.assertIn(keep, reply)

    def test_moderate_line_with_action_keeps_it(self) -> None:
        # CR-021 in đủ hướng xử trí ("→ hỏi thuốc chống đông") — tin đầu không được cắt mất hành động.
        self.reply = Reply(alerts=[Alert("CR-021", "MODERATE", "[CR-021] Rung nhĩ + Nhổ răng → Hỏi thuốc chống đông",
                                         "c", "d")])
        reply = self._send("BN rung nhĩ, nhổ R48")[-1]
        self.assertIn("- [CR-021] Rung nhĩ + Nhổ răng → Hỏi thuốc chống đông.", reply)

    def test_red_only_reply_also_offers_detail(self) -> None:
        self.reply = Reply(alerts=[HIGH_ALERT])
        reply = self._send("BN uống warfarin, kê ibuprofen")[-1]
        self.assertIn(reply_mod.DETAIL_HINT, reply)
        self.assertNotIn("Nguồn:", reply)

    def test_detail_sends_all_alert_blocks_with_sources(self) -> None:
        # Tự thử 28/11/2026: "chi tiết" in lại cả bản tin (kết luận, 📋…) nên BS phải đọc lại → chỉ gửi khối cảnh báo.
        self.reply = self.FULL
        self._send("BN uống warfarin, kê Alaxan")
        detail = "\n".join(self._send("chi tiết"))
        self.assertTrue(detail.startswith("🔴 Nguy cơ cao:"), detail)
        for keep in ("(Vì: NSAID ức chế tiểu cầu). Nguồn: DDInter (Major: X).", "[DDI-029] Paracetamol + Warfarin",
                     "Nguồn: DDInter (Moderate: Y).", bot_mod.AGENT_TEXT["FOOTER"]):
            self.assertIn(keep, detail)
        for gone in ("Em rà xong", "📋", "Đã đối chiếu"):
            self.assertNotIn(gone, detail)

    def test_detail_keeps_conditional_headers(self) -> None:
        self.reply = Reply(alerts=[HIGH_ALERT], together=True, needs_more=True)
        self._send("ibuprofen, warfarin")
        self.assertTrue(self._send("chi tiết")[0].startswith("🔴 Nguy cơ cao nếu dùng cùng nhau:"))

    def test_no_alert_no_detail_hint(self) -> None:
        self.reply = Reply(ok=bot_mod.AGENT_TEXT["OK"])
        self.assertNotIn(reply_mod.DETAIL_HINT, self._send("BN khoẻ, nhổ R38, kê paracetamol")[-1])

    def test_detail_without_recent_case(self) -> None:
        self.assertEqual(self._send("xem chi tiet"), [bot_mod.NO_DETAIL_TEXT])
        self.assertEqual(self.calls, [])

    def test_detail_uses_pending_case_without_merging(self) -> None:
        self.reply = Reply(alerts=[MODERATE_ALERT], together=True, needs_more=True)
        self._send("paracetamol, warfarin")
        self._send("chi tiết")
        self.assertEqual(self.calls, ["paracetamol, warfarin"])
        case = bot_mod._conv("chat_a").case
        self.assertEqual((case.text, case.waiting), ("paracetamol, warfarin", True))

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
        flagged = Reply(head=[bot_mod.PII_WARNING], checked=[("Thuốc đang dùng", "Sintrom")])
        bot_mod.ALLOWED_CHAT_IDS.add("chat-pii")
        try:
            with patch.object(bot_mod, "run_agent", return_value=(flagged, {})):
                update = _FakeUpdate("chat-pii", "BN Nguyễn Văn Test 65t uống Sintrom")
                asyncio.run(bot_mod.on_text(update, _FakeContext()))
        finally:
            bot_mod.ALLOWED_CHAT_IDS.discard("chat-pii")
        rec = self._records()[0]
        self.assertNotIn("Nguyễn Văn Test", json.dumps(rec, ensure_ascii=False))
        self.assertTrue(rec["pii_dropped"])
        self.assertEqual(update.message.replies, [reply_mod.render_chat(flagged) + "\n" + bot_mod.FOLLOW_UP_HINT])


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
        bot_mod._conversations.clear()
        self._patches = [
            patch.object(bot_mod, "run_agent", return_value=(_text_reply(), {"models": ["fake"]})),
            patch.object(bot_mod, "SEND_RETRY_SEC", 0, create=True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        bot_mod.LOG_DIR = self._orig_log_dir
        bot_mod.ALLOWED_CHAT_IDS = self._orig_allowed
        bot_mod._conversations.clear()
        self._tmpdir.cleanup()

    def _log_records(self) -> list[dict]:
        return [json.loads(line) for f in sorted(bot_mod.LOG_DIR.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines()]

    def _send(self, text: str) -> list[str]:
        upd = _FakeUpdate("chat_a", text)
        handler = bot_mod.on_feedback if text.startswith("/sai") else bot_mod.on_text
        asyncio.run(handler(upd, _FakeContext()))
        return upd.message.replies

    def test_log_failure_still_delivers_high_warning(self) -> None:
        # Review #33 (Nguyên) ý 1: log_turn đứng trước _reply_chunks; log lỗi thì BS mất cảnh báo đã tính xong.
        with patch.object(bot_mod, "run_agent", return_value=(Reply(alerts=[HIGH_ALERT]), {"models": ["fake"]})), \
                patch.object(bot_mod, "log_turn", side_effect=OSError("disk full")):
            replies = self._send("BN uống warfarin, kê ibuprofen")
        self.assertTrue(replies and replies[0].startswith("🔴 Nguy cơ cao:\n- [DDI-001]"), replies)
        self.assertNotIn(bot_mod.ERROR_TEXT, replies)

    def test_log_failure_keeps_dropped_note_on_agent_error(self) -> None:
        bot_mod._conv("chat_a").case = bot_mod.CaseState("Nhổ R48", Reply(), time.monotonic() - bot_mod.PENDING_TTL_SEC - 1,
                                                         waiting=True)
        with patch.object(bot_mod, "run_agent", side_effect=RuntimeError("model down")), \
                patch.object(bot_mod, "log_turn", side_effect=OSError("disk full")):
            replies = self._send("BN uống warfarin")
        self.assertTrue(replies and replies[0].startswith(bot_mod.DROPPED_NOTE), replies)

    def test_log_failure_still_acks_feedback_and_small_talk(self) -> None:
        with patch.object(bot_mod, "log_turn", side_effect=OSError("disk full")):
            self.assertEqual(self._send("/sai thiếu cảnh báo"), [bot_mod.FEEDBACK_ACK])
            replies = self._send("cảm ơn em")
        self.assertTrue(replies, replies)
        self.assertNotIn(bot_mod.ERROR_TEXT, replies)

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
