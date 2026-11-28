"""Test bot/log_stats.py bằng log giả (không đọc log thật).

Chạy từ gốc repo: python3 -m unittest bot/test_log_stats.py
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

_spec = importlib.util.spec_from_file_location("log_stats", Path(__file__).resolve().parent / "log_stats.py")
log_stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(log_stats)

RED2 = "🔴 Nguy cơ cao:\n- [DDI-001] a. Nguồn: x.\n- [CR-001] b. Nguồn: y.\nBS là người quyết định."
RED1 = "🔴 Nguy cơ cao:\n- [CR-001] b. Nguồn: y.\n🟡 Cần thận trọng:\n- [DDI-029] c. Nguồn: z."


def rec(ts, chat, inp, out, kind=None, error=""):
    r = {"ts": "2026-11-28T%s+00:00" % ts, "chat": chat, "input": inp, "output": out, "error": error}
    if kind:
        r["kind"] = kind
    return r


RECORDS = [
    rec("01:00:00", "c1", "chào em", log_stats.AGENT_TEXT["HELLO"], kind="small_talk"),
    rec("01:01:00", "c1", "BN uống warfarin, kê ibuprofen", RED2, kind="case"),
    rec("01:05:00", "c1", "thêm: đổi sang paracetamol", RED1, kind="case"),      # 🔴 giảm → đã sửa
    rec("02:00:00", "c2", "BN uống warfarin, kê ibuprofen", RED2),                # log cũ, không có kind
    rec("02:20:00", "c2", "BN uống aspirin", "✅ ok"),                             # quá 10 phút → để nguyên 🔴
    rec("03:00:00", "c3", "giá thuốc?", log_stats.OUT_OF_SCOPE["lieu"] + "\n" + log_stats.AGENT_TEXT["REPAIR"]),
    rec("03:01:00", "c3", "/sai DDI-029 thừa", log_stats.FEEDBACK_ACK),          # log cũ: nhận theo input
    rec("03:02:00", "c3", "chi tiết", "full", kind="detail"),
    rec("03:03:00", "c3", "abc", "", kind="case", error="RuntimeError: x"),
]


class LogStatsTests(unittest.TestCase):
    def test_counts(self):
        s = log_stats.compute(RECORDS)
        self.assertEqual(s["turns"], 9)
        self.assertEqual(s["by_kind"], {"small_talk": 1, "case": 6, "feedback": 1, "detail": 1})
        self.assertEqual(s["cases_with_high"], 3)
        self.assertEqual(s["cases_with_moderate"], 1)
        self.assertEqual(s["refusals"], {"lieu": 1})
        self.assertEqual(s["follow_up_them"], 1)
        self.assertEqual(s["repair"], 1)
        self.assertEqual(s["errors"], 1)

    def test_left_in_red_proxy(self):
        s = log_stats.compute(RECORDS)
        # c1 ca đầu: 2 🔴 → 1 🔴 trong 10 phút = đã sửa; c1 ca sau và c2: không có tin sau làm giảm 🔴.
        self.assertEqual(s["red_cases"], 3)
        self.assertEqual(s["left_in_red"], 2)

    def test_main_prints_numbers_only(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "20261128.jsonl"
            path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in RECORDS) + "\n{hỏng\n",
                            encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = log_stats.main([d])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("left_in_red", out)
        self.assertIn("bad_lines", out)
        for r in RECORDS:   # không in nội dung tin
            self.assertNotIn(r["input"], out)


if __name__ == "__main__":
    unittest.main()
