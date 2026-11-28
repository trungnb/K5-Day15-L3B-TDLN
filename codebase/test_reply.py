"""Test reply.py: ba cách in một Reply (eval / Zalo / "chi tiết") — chuyển từ bot/test_zalo_bot.py (issue #31)
khi bot thôi đọc ngược chuỗi output.

Chạy: python3 -m unittest codebase/test_reply.py   (từ gốc repo)
"""
import csv
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent  # noqa: E402
import reply as R  # noqa: E402
from reply import Alert, Reply  # noqa: E402
from texts import OUT_OF_SCOPE, TEXT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CODE = re.compile(r"\[(?:DDI|CR)-\d+\]")
CHECKED = [("Bệnh nền", "không khai"), ("Dị ứng", "không khai"), ("Thuốc đang dùng", "Warfarin (kháng vitamin K)"),
           ("Thủ thuật", "Nhổ răng / Tiểu phẫu răng khôn"), ("Thuốc định kê", "không khai")]
HIGH = Alert("CR-001", "HIGH", "[CR-001] Warfarin + Nhổ răng → Kiểm tra INR trước thủ thuật", "SDCEP (2022)",
             "[CR-001] Warfarin + Nhổ răng → Kiểm tra INR trước thủ thuật. (Vì: giảm đông). Nguồn: SDCEP (2022).")


def _recorded_replies():
    """(tin, các câu model đã trả) của từng câu trong eval/run-*.csv, lấy từ traces/run-*.jsonl."""
    for run in ("run-1", "run-2"):
        replies = {}
        for line in open(ROOT / "traces" / f"{run}.jsonl", encoding="utf-8"):
            event = json.loads(line)
            if event.get("kind") == "model" and event.get("case"):
                replies.setdefault(event["case"], []).append(event.get("output", ""))
        for row in csv.DictReader(open(ROOT / "eval" / f"{run}.csv", encoding="utf-8-sig")):
            yield row["input"], replies.get(row["id"], [])


def _replay(text, model_replies):
    queue = list(model_replies)

    def fake(system, user, json_mode=False):
        if not queue:
            raise RuntimeError("hết câu đã ghi")
        return {"text": queue.pop(0), "model": "replay", "tokens_in": 0, "tokens_out": 0}
    old_call, old_note = agent.call_model, agent.note
    agent.call_model, agent.note = fake, (lambda *a, **k: None)
    try:
        return agent.answer(text)
    finally:
        agent.call_model, agent.note = old_call, old_note


class RenderText(unittest.TestCase):
    def test_answer_output_is_render_text_of_reply(self):
        res = _replay("BN uống warfarin, nhổ R48", [json.dumps(
            {"conditions": [], "allergies": [], "baseline_drugs": ["warfarin"], "planned_procedures": ["nhổ R48"],
             "planned_drugs": [], "out_of_scope": [], "has_pii": False})])
        self.assertEqual(res["output"], R.render_text(res["reply"]))
        self.assertEqual(res["needs_more"], res["reply"].needs_more)

    def test_alert_line_carries_source(self):
        out = R.render_text(Reply(alerts=[HIGH], checked=CHECKED))
        self.assertIn("- [CR-001] Warfarin + Nhổ răng → Kiểm tra INR trước thủ thuật. Nguồn: SDCEP (2022).", out)
        self.assertIn(R.CHECKED_PREFIX + "Bệnh nền: không khai · Dị ứng: không khai", out)
        self.assertTrue(out.endswith(TEXT["FOOTER"]))


class RenderChat(unittest.TestCase):
    def test_checked_becomes_bullets_with_chua_khai(self):
        out = R.render_chat(Reply(verdict="Em rà xong rồi ạ — có 1 nguy cơ cao.", checked=CHECKED))
        self.assertIn("📋 Em đã đối chiếu:\n• Thuốc đang dùng: Warfarin (kháng vitamin K)\n"
                      "• Thủ thuật: Nhổ răng / Tiểu phẫu răng khôn\n• Chưa khai: bệnh nền, dị ứng, thuốc định kê", out)
        self.assertNotIn(R.CHECKED_PREFIX, out)
        self.assertTrue(out.endswith(TEXT["FOOTER"]))

    def test_q1_gets_lead_in_and_moi_hint(self):
        out = R.render_chat(Reply(question=TEXT["Q1"], question_key="Q1"))
        self.assertEqual(out, f"{R.ASK_LEAD}\n{TEXT['Q1']}\n{R.ASK_MOI_HINT}\n{TEXT['FOOTER']}")

    def test_repeat_miss_swaps_q1_for_template(self):
        out = R.render_chat(Reply(question=TEXT["Q1"], question_key="Q1"), repeat_miss=True)
        self.assertIn(TEXT["REPAIR"], out)
        self.assertNotIn(TEXT["Q1"], out)
        self.assertNotIn(R.ASK_LEAD, out)

    def test_refusal_gets_lead_in_but_emergency_line_does_not(self):
        out = R.render_chat(Reply(refusals=[OUT_OF_SCOPE["lieu"]], question=TEXT["Q1"], question_key="Q1"))
        self.assertTrue(out.startswith(f"{R.REFUSAL_LEAD}\n{OUT_OF_SCOPE['lieu']}\n"), out)
        self.assertNotIn(R.ASK_LEAD, out)            # câu dẫn từ chối đã đủ, không chồng thêm
        er = OUT_OF_SCOPE["cap_cuu"]
        self.assertTrue(R.render_chat(Reply(head=[er], verdict="Em rà xong rồi ạ — có 1 nguy cơ cao.")).startswith(er))

    def test_alerts_are_short_and_offer_detail(self):
        out = R.render_chat(Reply(alerts=[HIGH]))
        self.assertIn("- [CR-001] Warfarin + Nhổ răng → Kiểm tra INR trước thủ thuật.\n", out)
        self.assertNotIn("Nguồn:", out)
        self.assertTrue(out.endswith(R.DETAIL_HINT))
        self.assertNotIn(R.DETAIL_HINT, R.render_chat(Reply(ok=TEXT["OK"])))

    def test_chat_never_drops_codes_or_checked_values_on_recorded_cases(self):
        n = 0
        for text, model_replies in _recorded_replies():
            reply = _replay(text, model_replies)["reply"]
            chat, full = R.render_chat(reply), R.render_text(reply)
            self.assertEqual(sorted(CODE.findall(full)), sorted(CODE.findall(chat)), text)
            for label, value in reply.checked:
                if value != TEXT["NOT_DECLARED"]:
                    self.assertIn(value, chat, text)
            for line in reply.head + reply.notes + reply.refusals + [reply.verdict, reply.ok, reply.question]:
                self.assertIn(line, chat, text)
            n += 1
        self.assertGreaterEqual(n, 50)


class RenderDetail(unittest.TestCase):
    def test_detail_is_only_alert_blocks_with_reasons_and_sources(self):
        out = R.render_detail(Reply(verdict="Em rà xong rồi ạ — có 1 nguy cơ cao.", alerts=[HIGH], checked=CHECKED))
        self.assertEqual(out, "🔴 Nguy cơ cao:\n- " + HIGH.detail + "\n" + TEXT["FOOTER"])

    def test_detail_without_alerts_resends_chat_reply_without_hint(self):
        reply = Reply(ok=TEXT["OK"], checked=CHECKED)
        self.assertEqual(R.render_detail(reply), R.render_chat(reply))

    def test_no_entity_is_structural(self):
        self.assertTrue(Reply(question=TEXT["Q1"], question_key="Q1").is_no_entity)
        self.assertFalse(Reply(question=TEXT["Q1"], question_key="Q1", checked=CHECKED).is_no_entity)
        self.assertFalse(Reply(question=TEXT["Q1"], question_key="Q1", notes=["❔ Em chưa có dữ liệu cho: x"]).is_no_entity)


if __name__ == "__main__":
    unittest.main()
