"""Test offline cho agent.answer — không gọi model thật (thay call_model bằng bản giả).

Chạy: python3 -m unittest codebase/test_agent_offline.py   (từ gốc repo)
Giữ các bất biến của design §1/§7 và chặn lại 4 lỗi tìm thấy khi rà thiết kế 28/11:
  1. tình huống 3 (chỉ liệt kê thuốc) phải cảnh báo có điều kiện, không chỉ hỏi lại;
  2. tin mở đầu bằng kết luận, dòng cảnh báo dùng tên ngắn;
  3. khung dự phòng không được cắt mất hướng xử trí (vd ngưỡng INR của CR-001);
  4. lời nhắc Q4 không giữ ca chờ ghép (needs_more).
Thêm 28/11 (rà UX hội thoại): tin xã giao không bị trả lời như ca bệnh; Q5 chỉ BS câu trả lời ghép được;
tình huống 3 hỏi thẳng tên thuốc vừa nêu.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent  # noqa: E402

SAFE_PHRASES = ("tra cứu an toàn trước thủ thuật", "kiểm tra an toàn")

EXAMPLE = ("BN nam 65t, rung nhĩ uống Sintrom, ĐTĐ type 2 uống metformin. Dự kiến nhổ R48. "
           "Định kê Augmentin + Ibuprofen")
EXAMPLE_X = {"conditions": ["rung nhĩ", "ĐTĐ type 2"], "allergies": [], "baseline_drugs": ["Sintrom", "metformin"],
             "planned_procedures": ["nhổ R48"], "planned_drugs": ["Augmentin", "Ibuprofen"],
             "out_of_scope": [], "has_pii": False}
LIST_ONLY = "Cordarone, Klacid, Dexa — check tương tác"
LIST_ONLY_X = {"conditions": [], "allergies": [], "baseline_drugs": ["Cordarone", "Klacid", "Dexa"],
               "planned_procedures": [], "planned_drugs": [], "out_of_scope": [], "has_pii": False}
HEALTHY = "BN 25t khoẻ mạnh, nhổ R38, định kê Augmentin"
HEALTHY_X = {"conditions": [], "allergies": [], "baseline_drugs": [], "planned_procedures": ["nhổ R38"],
             "planned_drugs": ["Augmentin"], "out_of_scope": [], "has_pii": False}


def run(text, extracted, model2=None, detail=False):
    """Chạy answer() với model giả: lần 1 trả `extracted`, lần 2 trả `model2` (None → lỗi → khung dự phòng).
    detail=True gọi answer(text, detail=True) (bản tin đủ cho lệnh "chi tiết" của bot)."""
    def fake(system, user, json_mode=False):
        if system == agent.SYSTEM_EXTRACT:
            return {"text": json.dumps(extracted, ensure_ascii=False), "model": "stub", "tokens_in": 0, "tokens_out": 0}
        if model2 is None:
            raise RuntimeError("model 2 giả lỗi")
        return {"text": json.dumps(model2(json.loads(user)), ensure_ascii=False),
                "model": "stub", "tokens_in": 0, "tokens_out": 0}
    old_call, old_note = agent.call_model, agent.note
    agent.call_model, agent.note = fake, (lambda *a, **k: None)
    try:
        return agent.answer(text, detail=True) if detail else agent.answer(text)
    finally:
        agent.call_model, agent.note = old_call, old_note


def section_of(output, code):
    """Mức (HIGH / MODERATE / None) của dòng chứa mã, theo tiêu đề 🔴/🟡 gần nhất phía trên (như eval/grade.py)."""
    current = None
    for line in output.splitlines():
        if line.lstrip().startswith("🔴"):
            current = "HIGH"
        elif line.lstrip().startswith("🟡"):
            current = "MODERATE"
        elif re.match(r"^\s*(?:❔|🚫|✅|⚠️|đã đối chiếu|bs là người quyết định)", line, re.I):
            current = None
        if "[%s]" % code in line:
            return current
    return "MISSING"


class Invariants(unittest.TestCase):
    def check_invariants(self, output):
        self.assertIn("BS là người quyết định.", output)
        low = output.lower()
        for phrase in SAFE_PHRASES:
            low = low.replace(phrase, "")
        self.assertNotRegex(low, r"\ban toàn\b")

    def test_example_keeps_all_high_codes_with_source(self):
        out = run(EXAMPLE, EXAMPLE_X)["output"]
        self.check_invariants(out)
        for code in ("CR-001", "DDI-001"):
            self.assertEqual(section_of(out, code), "HIGH")
        for line in out.splitlines():
            if re.search(r"\[(?:DDI|CR)-\d+\]", line):
                self.assertIn("Nguồn:", line)


class Issue1ListOnly(unittest.TestCase):
    def test_list_only_warns_conditionally_and_still_asks(self):
        res = run(LIST_ONLY, LIST_ONLY_X)
        out = res["output"]
        self.assertEqual(section_of(out, "DDI-013"), "HIGH")   # Klacid + Cordarone
        self.assertEqual(section_of(out, "DDI-023"), "HIGH")   # Dexa + Cordarone
        self.assertIn("nếu", out.lower())                       # cảnh báo có điều kiện
        self.assertIn("?", out)                                 # vẫn hỏi lại vai trò
        self.assertTrue(res["needs_more"])
        self.assertNotIn("Thuốc đang dùng:", out)               # không tự gán vai trò (B04–B07)


class Issue2Layout(unittest.TestCase):
    def test_first_line_is_verdict_not_echo(self):
        out = run(EXAMPLE, EXAMPLE_X)["output"]
        first = out.splitlines()[0]
        self.assertNotIn("Đã đối chiếu", first)
        self.assertIn("2 nguy cơ cao", first)
        self.assertIn("3 cần thận trọng", first)   # gồm CR-021 rung nhĩ (thêm 28/11 trên main)

    def test_alert_lines_use_short_names(self):
        out = run(EXAMPLE, EXAMPLE_X)["output"]
        alert_lines = [l for l in out.splitlines() if re.search(r"\[(?:DDI|CR)-\d+\]", l)]
        self.assertTrue(alert_lines)
        for line in alert_lines:
            self.assertNotIn("kháng vitamin K)", line.split("→")[0])


class Issue3Fallback(unittest.TestCase):
    def test_fallback_keeps_inr_thresholds(self):
        out = run(EXAMPLE, EXAMPLE_X)["output"]
        line = next(l for l in out.splitlines() if "[CR-001]" in l)
        self.assertIn("INR < 4", line)
        self.assertIn("INR ≥ 4", line)

    def test_model_line_with_invented_number_is_rejected(self):
        def model2(rules):
            return {"lines": {r["rule_id"]: "[%s] %s + %s: nguy cơ. → Kiểm INR, ngưng 5 hôm." % (
                r["rule_id"], r["a"], r["b"]) for r in rules}}
        out = run(EXAMPLE, EXAMPLE_X, model2=model2)["output"]
        self.assertNotIn("5 hôm", out)

    def test_high_model_line_dropping_thresholds_is_rejected(self):
        def model2(rules):
            return {"lines": {r["rule_id"]: "[%s] %s + %s: tăng chảy máu. → Kiểm INR trước khi làm." % (
                r["rule_id"], r["a"], r["b"]) for r in rules}}
        out = run(EXAMPLE, EXAMPLE_X, model2=model2)["output"]
        line = next(l for l in out.splitlines() if "[CR-001]" in l)
        self.assertIn("INR < 4", line)

    def test_good_model_line_is_used(self):
        def model2(rules):
            return {"lines": {r["rule_id"]: "[%s] %s + %s: model viết gọn. → làm theo bảng." % (
                r["rule_id"], r["a"], r["b"]) for r in rules if r["rule_id"] == "DDI-027"}}
        # DDI-027 là MODERATE: từ 28/11 bản mặc định in dòng 🟡 gọn bằng code, dòng model chỉ dùng ở bản "chi tiết".
        out = run(EXAMPLE, EXAMPLE_X, model2=model2, detail=True)["output"]
        self.assertIn("model viết gọn", out)
        self.assertNotIn("model viết gọn", run(EXAMPLE, EXAMPLE_X, model2=model2)["output"])


class Issue4Q4(unittest.TestCase):
    def test_q4_reminder_does_not_hold_case(self):
        res = run(HEALTHY, HEALTHY_X)
        self.assertIn("✅", res["output"])
        self.assertIn("bệnh nền", res["output"])   # vẫn nhắc Q4
        self.assertFalse(res["needs_more"])


class SmallTalk(unittest.TestCase):
    """Tin xã giao ("Hi", "M làm được gì", "cảm ơn em") từng nhận Q1 + "BS là người quyết định." như một ca bệnh."""

    def test_greeting_gets_intro_without_model_or_case_text(self):
        for text in ("Hi", "chào em", "Còn onl ko", "M làm được gì", "em làm được gì vậy?", "hello bot"):
            res = run(text, {})   # extracted rỗng: nếu answer() gọi model 1 thì schema sai → JSON_ERROR
            out = res["output"]
            self.assertIn("Ví dụ:", out, text)
            self.assertNotIn("BS là người quyết định", out, text)
            self.assertNotIn("Đã đối chiếu", out, text)
            self.assertNotIn("Em đọc tin này chưa trọn", out, text)
            self.assertFalse(res["needs_more"], text)

    def test_thanks_gets_short_ack(self):
        for text in ("cảm ơn em", "Dạ em cảm ơn nhiều ạ!", "cam on", "ok em", "thanks"):
            res = run(text, {})
            self.assertTrue(res["output"].startswith("Dạ không có gì"), text)
            self.assertFalse(res["needs_more"], text)

    def test_case_with_greeting_still_runs_full_flow(self):
        res = run("Chào em. " + EXAMPLE, EXAMPLE_X)
        self.assertEqual(section_of(res["output"], "DDI-001"), "HIGH")
        self.assertIn("BS là người quyết định.", res["output"])

    def test_small_talk_reply_is_exported_for_bot(self):
        self.assertIsNotNone(agent.small_talk_reply("cảm ơn em"))
        self.assertIsNone(agent.small_talk_reply("BN uống Sintrom"))
        self.assertIsNone(agent.small_talk_reply("có"))   # có thể là câu trả lời Q5 → để luồng ca xử lý


class FollowUpAnswers(unittest.TestCase):
    def test_q5_tells_doctor_a_reply_the_merge_can_read(self):
        # Bot ghép "…\nBổ sung: <tin mới>" (design §9); "có" trơn không khớp alias thủ thuật, "gây tê" thì khớp.
        self.assertIn("gây tê", agent.TEXT["Q5"].split("Nếu có", 1)[1])


class DrugOnly(unittest.TestCase):
    def test_single_drug_question_names_the_drug(self):
        x = dict(LIST_ONLY_X, baseline_drugs=["Augmentin"])
        res = run("Augmentin", x)
        out = res["output"]
        self.assertIn("Amoxicillin", out.split("\n")[0])     # câu đầu hỏi thẳng thuốc vừa nêu
        self.assertIn("?", out.split("\n")[0])
        self.assertNotIn("không khai", out)                  # bỏ "Bệnh nền: không khai · Dị ứng: không khai"
        self.assertTrue(res["needs_more"])


def _x(**k):
    base = {"conditions": [], "allergies": [], "baseline_drugs": [], "planned_procedures": [], "planned_drugs": [],
            "out_of_scope": [], "has_pii": False}
    base.update(k)
    return base


class UnmappedWording(unittest.TestCase):
    """❔ từng khuyên BS "ghi rõ … hoạt chất" cho cả "tăng huyết áp" hay "lấy cao răng"."""

    def test_condition_and_procedure_do_not_ask_for_active_ingredient(self):
        out = run("BN tăng huyết áp, hen. Nạo túi nha chu, kê Augmentin",
                  _x(conditions=["tăng huyết áp", "hen"], planned_procedures=["nạo túi nha chu"],
                     planned_drugs=["Augmentin"]))["output"]
        # Bệnh nền chưa nhận ra → Q6 hỏi tên + tình trạng (run-2), không thêm ❔ trùng; thủ thuật → ❔ "chưa có quy tắc".
        self.assertIn(agent.TEXT["Q6"].format(names="tăng huyết áp, hen"), out)
        self.assertFalse(any(l.startswith("❔") and "tăng huyết áp" in l for l in out.splitlines()))
        line = next(l for l in out.splitlines() if l.startswith("❔") and "nạo túi nha chu" in l)
        self.assertNotIn("hoạt chất", line)
        self.assertIn("tự đánh giá", line)
        self.assertNotIn("✅", out)

    def test_unknown_drug_name_still_asks_for_active_ingredient(self):
        out = run("BN uống Zyxoltab. Nhổ R48, kê Augmentin",
                  _x(baseline_drugs=["Zyxoltab"], planned_procedures=["nhổ R48"], planned_drugs=["Augmentin"]))["output"]
        line = next(l for l in out.splitlines() if "Zyxoltab" in l and l.startswith("❔"))
        self.assertIn("hoạt chất", line)

    def test_patient_forgot_drug_name_gets_practical_ask_and_holds_case(self):
        # P5: "bệnh nhân không nhớ tên thuốc".
        res = run("BN uống thuốc chống đông không nhớ tên. Nhổ R48, kê Augmentin",
                  _x(baseline_drugs=["thuốc chống đông không nhớ tên"], planned_procedures=["nhổ R48"],
                     planned_drugs=["Augmentin"]))
        line = next(l for l in res["output"].splitlines() if "không nhớ tên" in l and l.startswith("❔"))
        self.assertIn("vỏ hộp", line)
        self.assertNotIn("hoạt chất", line)
        self.assertTrue(res["needs_more"])   # bot giữ ca để BS nhắn tên thuốc sau khi hỏi BN


class SeveralPatients(unittest.TestCase):
    def test_two_patients_in_one_message_are_not_mixed(self):
        for text in ("BN1 uống Sintrom nhổ R48. BN2 dị ứng penicillin, kê Augmentin",
                     "Ca 1: BN 60t uống aspirin. Ca 2: BN 30t có thai, kê ibuprofen"):
            res = run(text, EXAMPLE_X)
            self.assertIn("mỗi ca một tin", res["output"], text)
            self.assertNotIn("[", res["output"], text)   # không in cảnh báo trộn hai BN
            self.assertFalse(res["needs_more"], text)

    def test_single_numbered_patient_is_fine(self):
        res = run("BN1 uống Sintrom. Nhổ R48", _x(baseline_drugs=["Sintrom"], planned_procedures=["nhổ R48"]))
        self.assertEqual(section_of(res["output"], "CR-001"), "HIGH")


class ExtractPrompt(unittest.TestCase):
    def test_emergency_flag_points_to_emergency_care_and_keeps_checking(self):
        res = run("BN uống Sintrom, nhổ R48 xong chảy máu không cầm, kê thêm gì?",
                  _x(baseline_drugs=["Sintrom"], planned_procedures=["nhổ R48"], out_of_scope=["cap_cuu"]))
        out = res["output"]
        self.assertIn("cấp cứu", out)
        self.assertIn("115", out)
        self.assertEqual(section_of(out, "CR-001"), "HIGH")   # cờ không làm dừng luồng (design §6)

    def test_emergency_alone_never_prints_ok(self):
        out = run("BN khó thở sau tiêm tê, kê Augmentin", _x(planned_procedures=["tiêm tê"], planned_drugs=["Augmentin"],
                                                         out_of_scope=["cap_cuu"]))["output"]
        self.assertTrue(out.startswith("🚫 Em không hỗ trợ xử trí cấp cứu"))
        self.assertNotIn("✅", out)

    def test_emergency_does_not_also_print_generic_out_of_scope(self):
        # Gemini thật 28/11 trả cả "cap_cuu" lẫn "khac" cho "chảy máu không cầm … làm sao?" → 2 dòng 🚫 chồng nhau.
        out = run("BN uống Sintrom, nhổ R48 xong chảy máu không cầm, làm sao?",
                  _x(baseline_drugs=["Sintrom"], planned_procedures=["nhổ R48"], out_of_scope=["cap_cuu", "khac"]))["output"]
        self.assertNotIn("ngoài phạm vi", out)
        self.assertIn("cấp cứu", out)

    def test_prompt_says_written_dose_is_not_a_dose_question(self):
        self.assertIn("ghi sẵn liều", agent.SYSTEM_EXTRACT)
        self.assertIn('"cap_cuu"', agent.SYSTEM_EXTRACT)


EMPTY_X = {"conditions": [], "allergies": [], "baseline_drugs": [], "planned_procedures": [], "planned_drugs": [],
           "out_of_scope": [], "has_pii": False}
PAIR_ONLY = "paracetamol, warfarin"
PAIR_ONLY_X = dict(EMPTY_X, baseline_drugs=["paracetamol", "warfarin"])


def moderate_lines(output):
    lines, current = [], None
    for line in output.splitlines():
        if line.lstrip().startswith("🔴"):
            current = "HIGH"
        elif line.lstrip().startswith("🟡"):
            current = "MODERATE"
        elif not line.startswith("- "):
            current = None
        elif current == "MODERATE":
            lines.append(line)
    return lines


class Communication2811(unittest.TestCase):
    """Kế hoạch giao tiếp Trung duyệt 28/11: câu chào nói rõ AI, chào tạm biệt, nhận ra tin không có thực thể,
    bản tin gọn cho 🟡 (🔴 giữ nguyên), bản đủ khi bot gọi answer(text, detail=True)."""

    def test_hello_says_it_is_ai(self):
        self.assertIn("trợ lý AI", agent.TEXT["HELLO"])
        self.assertIn("trợ lý AI", agent.small_talk_reply("hi"))

    def test_bye_gets_short_goodbye(self):
        for text in ("tạm biệt", "bye em", "Bye bye!", "hẹn gặp lại nhé"):
            self.assertEqual(agent.small_talk_reply(text), agent.TEXT["BYE"], text)
            self.assertEqual(agent.small_talk_kind(text), "bye", text)

    def test_small_talk_kind_separates_greeting_from_help(self):
        self.assertEqual(agent.small_talk_kind("hi"), "greet")
        self.assertEqual(agent.small_talk_kind("em làm được gì"), "help")
        self.assertEqual(agent.small_talk_kind("cảm ơn em"), "thanks")
        self.assertIsNone(agent.small_talk_kind("BN uống Sintrom"))

    def test_no_entity_reply_is_detectable(self):
        self.assertTrue(agent.is_no_entity_reply(run("abc xyz", EMPTY_X)["output"]))
        self.assertFalse(agent.is_no_entity_reply(run(EXAMPLE, EXAMPLE_X)["output"]))
        self.assertFalse(agent.is_no_entity_reply(run(LIST_ONLY, LIST_ONLY_X)["output"]))

    def test_moderate_lines_are_compact_and_skip_model_2(self):
        sent = []
        def model2(payload):
            sent.extend(payload)
            return {"lines": {}}
        out = run(EXAMPLE, EXAMPLE_X, model2=model2)["output"]
        mods = moderate_lines(out)
        self.assertEqual(len(mods), 3)
        for line in mods:
            self.assertRegex(line, r"^- \[(?:DDI|CR)-\d+\] ")
            self.assertIn("Nguồn:", line)
            self.assertNotIn("→", line)            # không in hướng xử trí
        self.assertTrue(sent)
        self.assertTrue(all(item["rule_id"] in out for item in sent))
        mod_ids = {re.search(r"\[((?:DDI|CR)-\d+)\]", l).group(1) for l in mods}
        self.assertFalse(mod_ids & {item["rule_id"] for item in sent})   # model 2 chỉ viết dòng HIGH
        self.assertEqual(section_of(out, "CR-001"), "HIGH")
        self.assertIn("INR", out)                  # 🔴 vẫn đủ hướng xử trí

    def test_detail_mode_prints_full_moderate_guidance(self):
        sent = []
        def model2(payload):
            sent.extend(payload)
            return {"lines": {}}
        out = run(EXAMPLE, EXAMPLE_X, model2=model2, detail=True)["output"]
        mods = moderate_lines(out)
        self.assertEqual(len(mods), 3)
        for line in mods:
            self.assertIn("→", line)
            self.assertIn("Nguồn:", line)
        self.assertEqual(len(sent), 5)             # đủ 2 HIGH + 3 MODERATE

    def test_conditional_moderate_only_case_needs_no_model_2(self):
        calls = []
        def model2(payload):   # agent nuốt lỗi model 2 → phải đếm lời gọi, không raise
            calls.append(payload)
            return {"lines": {}}
        out = run(PAIR_ONLY, PAIR_ONLY_X, model2=model2)["output"]
        self.assertEqual(calls, [])
        self.assertEqual(section_of(out, "DDI-029"), "MODERATE")
        self.assertIn("nếu dùng cùng nhau", out)
        line = [l for l in out.splitlines() if "[DDI-029]" in l][0]
        self.assertIn("Nguồn:", line)


if __name__ == "__main__":
    unittest.main()
