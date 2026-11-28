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
import tools  # noqa: E402
from reply import render_detail  # noqa: E402

# 🟡 in đủ hướng xử trí (data/rule_behavior.csv)
FULL_MODERATE = {rid for rid in tools._behaviors() if tools.rule_behavior(rid)["show_full_guidance"]}

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
    detail=True trả bản "chi tiết" của cùng Reply (reply.render_detail) ở khoá output."""
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
        res = agent.answer(text)
        return dict(res, output=render_detail(res["reply"])) if detail else res
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
            return {"lines": {r["rule_id"]: "[%s] %s + %s → model viết gọn." % (
                r["rule_id"], r["a"], r["b"]) for r in rules if r["rule_id"] == "DDI-001"}}
        # Dòng model chỉ dùng ở bản mặc định; bản "chi tiết" in nguyên văn bảng tra bằng code (28/11).
        self.assertIn("model viết gọn", run(EXAMPLE, EXAMPLE_X, model2=model2)["output"])
        self.assertNotIn("model viết gọn", run(EXAMPLE, EXAMPLE_X, model2=model2, detail=True)["output"])


class Issue4Q4(unittest.TestCase):
    def test_q4_reminder_does_not_hold_case(self):
        # 28/11: thủ thuật không chảy máu (không hỏi Q8), BS không khai cả ba mục → nhắc Q4 mà không giữ ca.
        # Ghi "khoẻ mạnh" / "không dùng thuốc" thì mục đó là "không có", không nhắc Q4 (test_khong_tuong_tac).
        res = run("BN 25t, trám răng, định kê Paracetamol",
                  dict(HEALTHY_X, planned_procedures=["trám răng"], planned_drugs=["Paracetamol"]))
        self.assertIn("✅", res["output"])
        self.assertEqual(res["reply"].question_key, "Q4")
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
        self.assertIn("gây tê", agent.TEXT["Q5"].split("Có thì", 1)[1])


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
        # 28/11 (log VM 14:59): "chống đông" là tên nhóm → 🔴 CR-022, hướng xử trí nhờ hỏi tên thuốc (vỏ hộp, đơn).
        self.assertEqual(section_of(res["output"], "CR-022"), "HIGH")
        line = next(l for l in res["output"].splitlines() if "[CR-022]" in l)
        self.assertIn("vỏ hộp", line)
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

    def test_age_or_count_after_bn_or_ca_is_one_patient(self):
        # Review PR #30: "BN 7 tuổi", "ca 2 răng", "BN 1 tuần", "ca 3 ngày" là tuổi / số đếm, không phải số thứ tự BN.
        for text in ("BN 7 tuổi, dị ứng penicillin, ca 2 răng sữa cần nhổ",
                     "BN 1 tuần trước nhổ răng, ca 3 ngày nay sốt"):
            res = run(text, EXAMPLE_X)
            self.assertNotIn("mỗi ca một tin", res["output"], text)



ASK_ANTICOAG = "BN có dùng thuốc chống đông hoặc kháng tiểu cầu không? Có thì nhắn tên thuốc để em kiểm."


class AskAnticoagulant2811(unittest.TestCase):
    """Trung chốt 28/11: thủ thuật chảy máu mà chưa khai thuốc đang dùng → luôn hỏi thuốc chống đông / kháng tiểu cầu
    (thay cho việc thêm luật riêng cho từng bệnh: stent, van tim, đột quỵ…). Câu hỏi giữ ca chờ BS trả lời."""

    def test_stent_case_asks_and_holds(self):
        # Một câu mỗi lượt (28/11): Q6 (bệnh nền "đặt stent" chưa nhận ra) hỏi trước, BS trả lời xong mới tới Q8.
        x = _x(conditions=["đặt stent 6 tháng"], planned_procedures=["nhổ răng"])
        res = run("Bn đặt stent 6 tháng, giờ nhổ răng đc ko", x)
        self.assertIn("đặt stent 6 tháng", res["output"])
        self.assertNotIn(ASK_ANTICOAG, res["output"])
        self.assertTrue(res["needs_more"])
        res = run("Bn đặt stent 6 tháng, giờ nhổ răng đc ko\nBổ sung: không", x)
        self.assertIn(ASK_ANTICOAG, res["output"])
        self.assertTrue(res["needs_more"])

    def test_healthy_extraction_asks_and_has_no_green_check(self):
        res = run("Nhổ R48, kê paracetamol", _x(planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
        self.assertIn(ASK_ANTICOAG, res["output"])
        self.assertNotIn("✅", res["output"])
        self.assertTrue(res["needs_more"])

    def test_not_asked_when_baseline_drugs_declared(self):
        res = run("BN uống Sintrom. Nhổ R48", _x(baseline_drugs=["Sintrom"], planned_procedures=["nhổ R48"]))
        self.assertNotIn(ASK_ANTICOAG, res["output"])
        res = run("BN uống metformin. Nhổ R48, kê paracetamol",
                  _x(baseline_drugs=["metformin"], planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
        self.assertNotIn(ASK_ANTICOAG, res["output"])

    def test_not_asked_for_non_bleeding_procedure(self):
        res = run("Trám răng R36, kê paracetamol", _x(planned_procedures=["trám răng R36"], planned_drugs=["paracetamol"]))
        self.assertNotIn(ASK_ANTICOAG, res["output"])

    def test_not_asked_when_bs_says_no_medication(self):
        for text in ("BN không dùng thuốc gì. Nhổ R48, kê paracetamol", "bn ko uống thuốc, nhổ R48, kê paracetamol"):
            res = run(text, _x(planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
            self.assertNotIn(ASK_ANTICOAG, res["output"], text)

    def test_answer_merged_by_bot_brings_existing_rule(self):
        # Bot ghép câu trả lời vào ca đang chờ → thuốc nền có tên → luật sẵn có cảnh báo, không hỏi Q8 nữa.
        res = run("Bn đặt stent 6 tháng, giờ nhổ răng đc ko\nBổ sung: có, đang uống Plavix",
                  _x(conditions=["đặt stent 6 tháng"], baseline_drugs=["Plavix"], planned_procedures=["nhổ răng"]))
        self.assertIn("[CR-004]", res["output"])
        self.assertNotIn(ASK_ANTICOAG, res["output"])

    def test_bare_no_merged_by_bot_answers_q8(self):
        # Log VM 28/11: BS trả lời Q8 chỉ bằng "không" → bot hỏi lại Q8 mãi, ca không bao giờ chốt.
        for reply in ("không", "ko", "Không có", "k", "chưa", "dạ không ạ", "không dùng", "ko có thuốc gì"):
            res = run("Nhổ R48, kê paracetamol\nBổ sung: " + reply,
                      _x(planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
            self.assertNotIn(ASK_ANTICOAG, res["output"], reply)
            self.assertFalse(res["needs_more"], reply)

    def test_no_with_more_words_is_not_a_bare_no(self):
        # "không" kèm chữ khác (vd "không gây tê", "không nhớ tên") không phải câu trả lời Q8.
        for reply in ("không gây tê", "không nhớ tên thuốc", "không biết"):
            res = run("Nhổ R48, kê paracetamol\nBổ sung: " + reply,
                      _x(planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
            self.assertIn(ASK_ANTICOAG, res["output"], reply)

    def test_bare_no_outside_merged_line_does_not_answer_q8(self):
        # Chữ "không" trong tin gốc ("đau không") không phải câu trả lời Q8.
        res = run("Nhổ R48 đau không, kê paracetamol",
                  _x(planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
        self.assertIn(ASK_ANTICOAG, res["output"])

    def test_not_repeated_when_cr021_already_asks(self):
        res = run("BN rung nhĩ. Nhổ R18, kê paracetamol",
                  _x(conditions=["rung nhĩ"], planned_procedures=["nhổ R18"], planned_drugs=["paracetamol"]))
        self.assertIn("[CR-021]", res["output"])
        self.assertNotIn(ASK_ANTICOAG, res["output"])

class OneQuestionPerTurn2811(unittest.TestCase):
    """Trung chốt 28/11: mỗi lượt chỉ hỏi MỘT câu (thứ tự Q5, Q7, Q6, Q8, Q2, Q3) để "không" trơn luôn rõ trả lời câu
    nào. Mỗi dòng bot ghép "Bổ sung: …" trả lời câu đang hỏi lúc đó; "không" trơn đóng câu đó, lượt sau hỏi câu kế."""

    Q2 = agent.TEXT["Q2"]
    Q4 = agent.TEXT["Q4"]
    Q5 = agent.TEXT["Q5"]
    Q7 = agent.TEXT["Q7"]
    BLEED_X = _x(conditions=["rối loạn đông máu"], planned_procedures=["nhổ răng"])
    LA_X = _x(allergies=["thuốc tê"], planned_procedures=["lấy cao dưới nướu"], planned_drugs=["paracetamol"])
    STENT_X = _x(conditions=["đặt stent 6 tháng"], planned_procedures=["nhổ răng"])

    def _questions(self, out):
        return [q for q in (self.Q5, self.Q7, "em chưa nhận ra. Anh/chị ghi rõ", ASK_ANTICOAG, self.Q2,
                            agent.TEXT["Q3"]) if q in out]

    def test_only_one_question_and_no_q4_while_asking(self):
        res = run("Nhổ R48", _x(planned_procedures=["nhổ R48"]))
        self.assertEqual(self._questions(res["output"]), [ASK_ANTICOAG])
        self.assertNotIn(self.Q4, res["output"])
        self.assertTrue(res["needs_more"])

    def test_bare_no_closes_shown_question_then_next_one(self):
        x = _x(planned_procedures=["nhổ R48"])
        res = run("Nhổ R48\nBổ sung: không", x)
        self.assertEqual(self._questions(res["output"]), [self.Q2])
        self.assertTrue(res["needs_more"])
        res = run("Nhổ R48\nBổ sung: không\nBổ sung: ko", x)
        self.assertEqual(self._questions(res["output"]), [])
        self.assertIn(self.Q4, res["output"])   # hết câu hỏi mới nhắc Q4
        self.assertFalse(res["needs_more"])

    def test_q5_first_and_bare_no_means_no_anesthesia(self):
        res = run("BN dị ứng thuốc tê. Lấy cao dưới nướu, kê paracetamol", self.LA_X)
        self.assertEqual(self._questions(res["output"]), [self.Q5])
        res = run("BN dị ứng thuốc tê. Lấy cao dưới nướu, kê paracetamol\nBổ sung: không", self.LA_X)
        self.assertEqual(self._questions(res["output"]), [ASK_ANTICOAG])

    def test_q7_first_and_stage_reply_closes_it(self):
        text = "Bn rối loạn đông máu trong quá trình nhổ răng"
        res = run(text, self.BLEED_X)
        self.assertEqual(self._questions(res["output"]), [self.Q7])
        self.assertIn("[CR-016]", res["output"])
        for reply in ("đang chuẩn bị, chưa nhổ", "không"):
            res = run(text + "\nBổ sung: " + reply, self.BLEED_X)
            self.assertEqual(self._questions(res["output"]), [ASK_ANTICOAG], reply)

    def test_q6_before_q8_and_unknown_condition_stays_visible(self):
        text = "Bn đặt stent 6 tháng, giờ nhổ răng đc ko"
        res = run(text, self.STENT_X)
        self.assertEqual(self._questions(res["output"]), ["em chưa nhận ra. Anh/chị ghi rõ"])
        res = run(text + "\nBổ sung: không", self.STENT_X)
        self.assertEqual(self._questions(res["output"]), [ASK_ANTICOAG])
        self.assertIn("❔", res["output"])                 # bệnh nền chưa nhận ra vẫn hiện, không mất
        self.assertIn("đặt stent 6 tháng", res["output"])

    def test_reply_with_words_does_not_close_q8(self):
        res = run("Nhổ R48\nBổ sung: để em hỏi lại BN", _x(planned_procedures=["nhổ R48"]))
        self.assertEqual(self._questions(res["output"]), [ASK_ANTICOAG])


class GeneralMatching2811(unittest.TestCase):
    """Log VM 28/11 — sửa tổng quát, không thêm từng alias: (1) tin xã giao viết liền không dấu cách ("Huongdan");
    (2) bệnh nền đã biết tên và BS đã ghi tình trạng ("tăng huyết áp đang ổn định") thì không hỏi lại Q6."""

    Q6_MARK = "em chưa nhận ra. Anh/chị ghi rõ"

    def test_small_talk_without_spaces(self):
        for text, kind in (("Huongdan", "help"), ("xinchao", "greet"), ("camon em", "thanks"), ("tambiet", "bye"),
                           ("lamduocgi", "help")):
            self.assertEqual(agent.small_talk_kind(text), kind, text)
        self.assertIsNone(agent.small_talk_kind("nhorang"))

    def _case(self, condition):
        return run("BN %s. Nhổ R48, kê paracetamol" % condition,
                   _x(conditions=[condition], planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))

    def test_known_condition_with_status_is_not_asked_again(self):
        for condition in ("tăng huyết áp đang ổn định", "THA ổn định", "huyết áp đã kiểm soát tốt"):
            out = self._case(condition)["output"]
            self.assertNotIn(self.Q6_MARK, out, condition)
            self.assertIn("❔ Em chưa có quy tắc cho: " + condition, out)   # vẫn hiện, BS tự đánh giá
            self.assertNotIn("✅", out)

    def test_q6_still_asked_when_name_unknown(self):
        for condition in ("th áp đang điều trị", "đặt stent 6 tháng"):
            self.assertIn(self.Q6_MARK, self._case(condition)["output"], condition)


class LogCase1228(unittest.TestCase):
    """Log VM 28/11 12:28: "Bn 65t sử dụng amlodipin cao huyết áp. Dự kiến điều trị tuỷ r16 gây tê bằng lidocain.
    Kê đơn: vigentin + paracetamol". (1) Bệnh có tên trong bảng nhưng chưa ghi tình trạng → chỉ hỏi mức kiểm soát,
    không nói "chưa nhận ra". (2) Thuốc tê / co mạch là thuốc của thủ thuật, không phải thuốc định kê: không liệt kê
    trong cặp "chưa có quy tắc", không hiện ở "Thuốc định kê"/"chưa rõ vai", nhưng vẫn được tra (DDI-020) và kéo theo
    nhóm gây tê (CR-014)."""

    TEXT = ("Bn 65t sử dụng amlodipin cao huyết áp. Dự kiến điều trị tuỷ r16 gây tê bằng lidocain. "
            "Kê đơn: vigentin + paracetamol")

    def test_known_condition_without_status_asks_only_status(self):
        for condition in ("cao huyết áp", "tăng huyết áp", "THA"):
            res = run("BN %s. Nhổ R48, kê paracetamol" % condition,
                      _x(conditions=[condition], planned_procedures=["nhổ R48"], planned_drugs=["paracetamol"]))
            out = res["output"]
            self.assertNotIn("em chưa nhận ra", out, condition)
            self.assertIn(agent.TEXT["Q6_STATUS"].format(names=condition), out, condition)
            self.assertTrue(res["needs_more"], condition)
            self.assertIn("Bệnh nền: %s ·" % condition, out, condition)   # tên đã nhận ra, không ghi "chưa nhận ra"

    def test_anesthetic_in_procedure_is_not_a_planned_drug(self):
        out = run(self.TEXT, _x(conditions=["cao huyết áp"], baseline_drugs=["amlodipin"],
                                planned_procedures=["điều trị tuỷ r16", "gây tê bằng lidocain"],
                                planned_drugs=["vigentin", "paracetamol"]))["output"]
        self.assertNotIn("Lidocaine +", out)
        self.assertNotIn("+ Lidocaine", out)
        checked = next(l for l in out.splitlines() if l.startswith("Đã đối chiếu"))
        self.assertNotIn("chưa rõ vai", checked)
        planned = checked.split("Thuốc định kê:")[1]
        self.assertNotIn("Lidocaine", planned)
        self.assertIn("Lidocaine", checked.split("Thủ thuật:")[1].split("·")[0])

    def test_anesthetic_named_only_in_text_is_not_listed_in_pairs(self):
        out = run("BN tăng huyết áp chưa kiểm soát. Nội nha R16, dùng lidocain. Kê paracetamol",
                  _x(conditions=["tăng huyết áp chưa kiểm soát"], planned_procedures=["nội nha R16"],
                     planned_drugs=["paracetamol"]))["output"]
        self.assertEqual(section_of(out, "CR-014"), "HIGH")
        self.assertNotIn("Lidocaine +", out)
        self.assertNotIn("+ Lidocaine", out)

    def test_anesthetic_is_not_a_drug_the_patient_takes(self):
        # Thuốc tê không phải "thuốc đang dùng": thủ thuật chảy máu chưa khai thuốc nền vẫn phải hỏi Q8.
        out = run("Nhổ R48 gây tê lidocain, kê paracetamol",
                  _x(planned_procedures=["nhổ R48", "gây tê lidocain"], planned_drugs=["paracetamol"]))["output"]
        self.assertIn(agent.TEXT["Q8"], out)

    def test_vasoconstrictor_still_checked_against_baseline_drugs(self):
        out = run("BN đang uống propranolol. Nhổ R48, gây tê Lignospan. Kê paracetamol",
                  _x(baseline_drugs=["propranolol"], planned_procedures=["nhổ R48", "gây tê Lignospan"],
                     planned_drugs=["paracetamol"]))["output"]
        self.assertEqual(section_of(out, "DDI-020"), "HIGH")


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
    bản tin gọn cho 🟡 (🔴 giữ nguyên), bản đủ cho lệnh "chi tiết" (reply.render_detail)."""

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

    def test_cr021_is_printed_in_full_in_compact_mode(self):
        # Trung chốt 28/11: CR-021 (rung nhĩ × thủ thuật chảy máu) có giá trị ở câu "hỏi thuốc chống đông" (guidance),
        # nên in đủ cả khi 🟡 gọn — dòng gọn chỉ còn câu đầu cơ chế, mất cả nguy cơ chảy máu lẫn hành động.
        af = _x(conditions=["rung nhĩ"], planned_procedures=["nhổ R18"], planned_drugs=["paracetamol"])
        sent = []
        def model2(payload):
            sent.extend(item["rule_id"] for item in payload)
            return {"lines": {}}
        res = run("BN rung nhĩ. Nhổ R18, kê paracetamol", af, model2)
        self.assertIn("CR-021", sent)
        self.assertEqual(section_of(res["output"], "CR-021"), "MODERATE")
        line = next(l for l in res["output"].splitlines() if "[CR-021]" in l)
        self.assertIn("thuốc chống đông hay kháng tiểu cầu", line)

    def test_no_entity_reply_is_detectable(self):
        self.assertTrue(run("abc xyz", EMPTY_X)["reply"].is_no_entity)
        self.assertFalse(run(EXAMPLE, EXAMPLE_X)["reply"].is_no_entity)
        self.assertFalse(run(LIST_ONLY, LIST_ONLY_X)["reply"].is_no_entity)

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
            if not any("[%s]" % rid in line for rid in FULL_MODERATE):
                self.assertNotIn("→", line)        # không in hướng xử trí (trừ CR-021, in đủ)
        self.assertTrue(sent)
        self.assertTrue(all(item["rule_id"] in out for item in sent))
        mod_ids = {re.search(r"\[((?:DDI|CR)-\d+)\]", l).group(1) for l in mods}
        # model 2 chỉ viết dòng HIGH và dòng 🟡 in đủ (CR-021)
        self.assertEqual(mod_ids & {item["rule_id"] for item in sent}, mod_ids & FULL_MODERATE)
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
            self.assertIn("(Vì: ", line)
            self.assertIn("Nguồn:", line)
        # bản đủ in nguyên văn bảng tra bằng code: model 2 chỉ được gọi cho tin đầu (HIGH + CR-021), không cho 🟡 gọn
        self.assertEqual({item["rule_id"] for item in sent} & {re.search(r"\[((?:DDI|CR)-\d+)\]", l).group(1)
                                                              for l in mods}, FULL_MODERATE & {"CR-021"})

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


class ConciseReply2811(unittest.TestCase):
    """Trung duyệt 28/11: tin trả lời gọn hơn nhưng giữ mã, cặp, hướng xử trí và nguồn. Lý do "(Vì: …)" của dòng 🔴
    chỉ in ở bản "chi tiết"; câu hỏi cuối tin không nhắc lại điều mục "Đã đối chiếu" đã ghi ("không khai")."""

    @staticmethod
    def _model2(rules):
        return {"lines": {r["rule_id"]: "[%s] %s + %s → %s. (Vì: lý do mẫu)" % (
            r["rule_id"], r["a"], r["b"], r["guidance"].rstrip(" .")) for r in rules}}

    def test_high_line_drops_reason_but_keeps_action_and_source(self):
        out = run(EXAMPLE, EXAMPLE_X, model2=self._model2)["output"]
        line = next(l for l in out.splitlines() if "[CR-001]" in l)
        self.assertNotIn("Vì:", out)
        self.assertIn("INR < 4", line)
        self.assertIn("Nguồn:", line)

    def test_detail_prints_table_text_verbatim(self):
        # Dòng model viết gọn có thể bỏ ý (vd "xin hội chẩn" của CR-001) mà bước kiểm số không bắt được →
        # bản "chi tiết" in nguyên văn guidance + mechanism + nguồn từ bảng tra.
        from tools import check_clinical_risks, normalize_entities
        out = run(EXAMPLE, EXAMPLE_X, model2=self._model2, detail=True)["output"]
        self.assertNotIn("lý do mẫu", out)
        n = normalize_entities(EXAMPLE_X, EXAMPLE)
        cr001 = next(r for r in check_clinical_risks(n["conditions"], n["allergies"], n["baseline_drugs"],
                                                     n["planned_drugs"], n["procedure_groups"]) if r["rule_id"] == "CR-001")
        line = next(l for l in out.splitlines() if "[CR-001]" in l)
        self.assertIn(cr001["guidance"].strip().rstrip(" ."), line)
        self.assertIn("(Vì: " + cr001["mechanism"].strip().rstrip(" ."), line)

    def test_questions_do_not_repeat_not_declared(self):
        x = dict(HEALTHY_X, planned_drugs=[])
        out = run("BN 25t khoẻ mạnh, nhổ R38", x)["output"]
        self.assertIn("Thuốc định kê: không khai", out)
        self.assertNotIn("chưa có thuốc định kê", out)
        for key in ("Q2", "Q3", "Q4"):
            self.assertFalse(agent.TEXT[key].startswith("Ca này chưa"), key)


class DetailFromSameReply2811(unittest.TestCase):
    """ "chi tiết" in lại CHÍNH bản tin đã trả (reply.render_detail) — không gọi lại model, nên mã cảnh báo không đổi
    giữa hai tin (trước 28/11 bot gọi lại answer(text, detail=True) và phải nhớ kết quả model 1 để giữ được điều này)."""

    def test_detail_has_same_codes_without_new_model_call(self):
        calls = []

        def fake(system, user, json_mode=False):
            calls.append(system)
            if system == agent.SYSTEM_EXTRACT:
                return {"text": json.dumps(EXAMPLE_X, ensure_ascii=False), "model": "stub", "tokens_in": 0, "tokens_out": 0}
            raise RuntimeError("model 2 giả lỗi")
        old_call, old_note = agent.call_model, agent.note
        agent.call_model, agent.note = fake, (lambda *a, **k: None)
        try:
            res = agent.answer(EXAMPLE)
            n_calls = len(calls)
            detail = render_detail(res["reply"])
        finally:
            agent.call_model, agent.note = old_call, old_note
        self.assertEqual(len(calls), n_calls)
        codes = lambda o: sorted(set(re.findall(r"\[(?:DDI|CR)-\d+\]", o)))
        self.assertEqual(codes(res["output"]), codes(detail))


if __name__ == "__main__":
    unittest.main()


class NearMatchSpelling2811(unittest.TestCase):
    """Log VM 28/11 14:57: "Dị ứng peniciline định cho augmentin được ko" → bot chỉ báo ❔, sót 🔴 CR-008.
    Trung chọn 28/11: tên hơi sai chính tả vẫn phải nhận ra (so gần đúng với tên trong bảng), và tin ghi rõ
    "em hiểu … là …" để BS thấy chỗ bot đoán."""

    def test_misspelled_allergen_still_fires_high_alert(self):
        res = run("Dị ứng peniciline định cho augmentin được ko",
                  _x(allergies=["peniciline"], planned_drugs=["augmentin"]))
        out = res["output"]
        self.assertEqual(section_of(out, "CR-008"), "HIGH")
        self.assertIn('"peniciline"', next(l for l in out.splitlines() if l.startswith("🔎")))
        self.assertNotIn("❔ Em chưa có quy tắc cho: peniciline", out)

    def test_misspelled_drug_names_are_recognised(self):
        for typo in ("wafarine", "warfarim", "ibuprofene", "aspirn"):
            out = run("BN uống %s, nhổ R48, kê augmentin" % typo,
                      _x(baseline_drugs=[typo], planned_procedures=["nhổ R48"], planned_drugs=["augmentin"]))["output"]
            self.assertIn("🔎", out, typo)
            self.assertNotIn("❔ Em chưa có dữ liệu cho: " + typo, out, typo)

    def test_unknown_or_short_words_are_not_forced_onto_table_names(self):
        for word in ("hen", "abc", "paroxetin", "thuốc lạ xyz"):
            out = run("BN uống %s, nhổ R48, kê augmentin" % word,
                      _x(baseline_drugs=[word], planned_procedures=["nhổ R48"], planned_drugs=["augmentin"]))["output"]
            self.assertNotIn("🔎", out, word)


class ClassNameAndAmpicillin2811(unittest.TestCase):
    """Log VM 28/11 15:34: BN mang thai + "kê NSAID được không" → ❔ "chưa có dữ liệu cho: NSAID", trượt 🔴 CR-013.
    Log 15:31: "dị ứng ampicilin" không nhận ra (bảng chỉ có amoxicillin). Trung duyệt alias 28/11."""

    def test_nsaid_class_name_fires_class_rules(self):
        res = run("BN mang thai, kê NSAID được không", _x(conditions=["mang thai"], planned_drugs=["NSAID"]))
        self.assertEqual(section_of(res["output"], "CR-013"), "HIGH")
        self.assertNotIn("chưa có dữ liệu cho: NSAID", res["output"])
        # Rule riêng từng thuốc (vd DDI-004 ibuprofen + aspirin) cần tên: nói rõ em mới kiểm theo nhóm.
        self.assertIn("em mới kiểm theo nhóm", res["output"])

    def test_named_nsaid_replaces_the_class_name(self):
        n = tools.normalize_entities(_x(planned_drugs=["NSAID ibuprofen"]), "kê NSAID ibuprofen")
        self.assertEqual([d["canonical_id"] for d in n["planned_drugs"]], ["ibuprofen"])

    def test_negated_nsaid_in_text_is_not_added(self):
        n = tools.normalize_entities(_x(planned_drugs=["paracetamol"]), "không dùng NSAID, kê paracetamol")
        self.assertNotIn("nsaid_unspecified", [d["canonical_id"] for d in n["planned_drugs"] + n["baseline_drugs"]])

    def test_ampicillin_allergy_and_drug(self):
        out = run("BN dị ứng ampicilin, nhổ R48, kê augmentin",
                  _x(allergies=["ampicilin"], planned_procedures=["nhổ R48"], planned_drugs=["augmentin"]))["output"]
        self.assertEqual(section_of(out, "CR-008"), "HIGH")
        out = run("BN dị ứng penicillin, nhổ R48, kê ampicillin",
                  _x(allergies=["penicillin"], planned_procedures=["nhổ R48"], planned_drugs=["ampicillin"]))["output"]
        self.assertEqual(section_of(out, "CR-008"), "HIGH")


class DeniedGroups2811(unittest.TestCase):
    """Log VM 28/11 15:37: BS ghi "không có bệnh nền, không dị ứng thuốc" mà mục 📋 vẫn ghi "Chưa khai: bệnh nền, dị ứng".
    BS phủ nhận cả nhóm thì ghi "không có"; phủ nhận MỘT thuốc / một dị ứng cụ thể thì không tính."""

    def test_denied_groups(self):
        cases = {
            "BN nam 58 tuổi, không có bệnh nền, không dị ứng thuốc. Đang dùng warfarin.": {"conditions", "allergies"},
            "giờ bệnh nhân không có bệnh lý gì, nhổ răng": {"conditions"},
            "BN khỏe mạnh, ko dị ứng gì, không dùng thuốc gì. Nhổ R48": {"conditions", "allergies", "baseline_drugs"},
            "không dị ứng penicillin, nhổ R48": set(),
            "không dùng thuốc chống đông, nhổ R48": set(),
            "không có bệnh nền gì ngoài tăng huyết áp": set(),
        }
        for text, want in cases.items():
            self.assertEqual(tools.declared_none(text), want, text)

    def test_checked_line_says_none_for_denied_groups(self):
        text = ("BN nam 58 tuổi, không có bệnh nền, không dị ứng thuốc. Đang dùng warfarin. Chuẩn bị nhổ 1 răng hàm dưới, "
                "định kê amoxicillin và paracetamol.")
        out = run(text, _x(baseline_drugs=["warfarin"], planned_procedures=["nhổ 1 răng hàm dưới"],
                           planned_drugs=["amoxicillin", "paracetamol"]))["output"]
        self.assertIn("Bệnh nền: không có", out)
        self.assertIn("Dị ứng: không có", out)
        self.assertNotIn("Bệnh nền: không khai", out)

    def test_named_entity_wins_over_denial(self):
        out = run("BN không có bệnh nền gì, tăng huyết áp ổn định, nhổ R48",
                  _x(conditions=["tăng huyết áp ổn định"], planned_procedures=["nhổ R48"]))["output"]
        self.assertNotIn("Bệnh nền: không có", out)


class UnnamedAnticoagulant2811(unittest.TestCase):
    """Log VM 28/11 14:59: "Bn uống chống đông nhổ răng được ko" → chỉ ❔ "chưa có dữ liệu cho: chống đông".
    Trung chọn 28/11: tên nhóm thuốc chưa rõ tên → 🔴 CR-022 (chống đông) / 🟡 CR-023 (kháng tiểu cầu) × thủ thuật
    chảy máu, hướng xử trí theo SDCEP 2022, và giữ ca để BS nhắn tên thuốc."""

    def test_unnamed_anticoagulant_before_extraction_is_high(self):
        res = run("Bn uống chống đông nhổ răng được ko", _x(baseline_drugs=["chống đông"], planned_procedures=["nhổ răng"]))
        out = res["output"]
        self.assertEqual(section_of(out, "CR-022"), "HIGH")
        self.assertNotIn("Em chưa có dữ liệu cho: chống đông", out)
        self.assertTrue(res["needs_more"])

    def test_unnamed_antiplatelet_is_moderate_with_action(self):
        res = run("BN uống thuốc kháng tiểu cầu, nhổ R48",
                  _x(baseline_drugs=["thuốc kháng tiểu cầu"], planned_procedures=["nhổ R48"]))
        self.assertEqual(section_of(res["output"], "CR-023"), "MODERATE")
        self.assertIn("→", next(l for l in res["output"].splitlines() if "[CR-023]" in l))
        self.assertTrue(res["needs_more"])

    def test_named_drug_replaces_the_unnamed_rule(self):
        out = run("BN uống chống đông warfarin, nhổ R48",
                  _x(baseline_drugs=["chống đông warfarin"], planned_procedures=["nhổ R48"]))["output"]
        self.assertEqual(section_of(out, "CR-001"), "HIGH")
        self.assertNotIn("CR-022", out)

    def test_any_named_antithrombotic_answers_the_name_question(self):
        # Log VM 28/11 15:29: BS hỏi tên xong nhắn "đang uống aspirin" → vẫn còn 🔴 CR-022 cạnh CR-005.
        # BS hay gọi chung aspirin / clopidogrel là "chống đông": có tên thuốc chống huyết khối nào thì bỏ dòng chưa rõ tên.
        for named, code in (("aspirin", "CR-005"), ("clopidogrel", "CR-004"), ("warfarin", "CR-001")):
            for unnamed, rule in (("chống đông", "CR-022"), ("thuốc kháng tiểu cầu", "CR-023")):
                out = run("BN uống %s, %s. Nhổ R48" % (unnamed, named),
                          _x(baseline_drugs=[unnamed, named], planned_procedures=["nhổ R48"]))["output"]
                self.assertIn(code, out, (unnamed, named))
                self.assertNotIn(rule, out, (unnamed, named))

    def test_negated_mention_in_text_does_not_fire(self):
        out = run("BN không dùng thuốc chống đông, nhổ R48, kê augmentin",
                  _x(planned_procedures=["nhổ R48"], planned_drugs=["augmentin"]))["output"]
        self.assertNotIn("CR-022", out)
