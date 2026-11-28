"""Test offline cho cải tiến lượt 2: chỉ rõ phần còn thiếu (hỏi lại dữ kiện, giới hạn bảng tra).

Không gọi model thật: thay agent.call_model bằng hàm giả trả JSON trích xuất cố định;
model lần 2 trả chuỗi rỗng → code dùng khung §7. Chạy: python3 -m unittest codebase/test_agent_hoi_lai.py
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402

EMPTY = {"conditions": [], "allergies": [], "baseline_drugs": [], "planned_procedures": [],
         "planned_drugs": [], "out_of_scope": [], "has_pii": False}


def run(text, **extracted):
    data = dict(EMPTY, **extracted)

    def fake_call_model(system, user, json_mode=False):
        body = json.dumps(data, ensure_ascii=False) if system == agent.SYSTEM_EXTRACT else ""
        return {"text": body, "model": "fake", "tokens_in": 0, "tokens_out": 0}

    original = agent.call_model
    agent.call_model = fake_call_model
    try:
        return agent.answer(text)
    finally:
        agent.call_model = original


class HoiLaiTests(unittest.TestCase):
    def test_b11_in_progress_bleeding_asks_stage(self):
        out = run("Bn rối loạn đông máu trong quá trình nhổ răng",
                  conditions=["rối loạn đông máu"], planned_procedures=["nhổ răng"])
        self.assertIn("[CR-016]", out["output"])
        self.assertIn(agent.TEXT["Q7"], out["output"])
        self.assertTrue(out["needs_more"])

    def test_planned_extraction_without_progress_words_does_not_ask_stage(self):
        out = run("BN đang dùng warfarin, dự kiến nhổ một răng đơn giản.",
                  baseline_drugs=["warfarin"], planned_procedures=["nhổ một răng"])
        self.assertIn("[CR-001]", out["output"])
        self.assertNotIn(agent.TEXT["Q7"], out["output"])

    def test_generic_trong_qua_trinh_does_not_ask_stage(self):
        out = run("Trong quá trình dùng warfarin, cần nhổ răng 38.",
                  baseline_drugs=["warfarin"], planned_procedures=["nhổ răng 38"])
        self.assertNotIn(agent.TEXT["Q7"], out["output"])

    def test_negated_bleeding_does_not_ask_stage(self):
        out = run("BN đang dùng warfarin, nhổ răng xong, không chảy máu khó cầm, không đang chảy máu.",
                  baseline_drugs=["warfarin"], planned_procedures=["nhổ răng"])
        self.assertNotIn(agent.TEXT["Q7"], out["output"])

    def test_stage_question_suppresses_ok_line(self):
        out = run("BN khoẻ, đang nhổ răng thì hỏi có cần lưu ý gì.", planned_procedures=["nhổ răng"])
        self.assertIn(agent.TEXT["Q7"], out["output"])
        self.assertNotIn(agent.TEXT["OK"], out["output"])

    def test_duplicate_unmapped_condition_listed_once(self):
        out = run("Bn th áp cần nhổ răng", conditions=["th áp", "th áp"], planned_procedures=["nhổ răng"])
        self.assertIn(agent.TEXT["Q6"].format(names="th áp"), out["output"])

    def test_b12_unmapped_condition_asks_name_and_control(self):
        out = run("Bn th áp đang điều trị cần nhổ răng",
                  conditions=["th áp đang điều trị"], planned_procedures=["nhổ răng"])
        self.assertIn(agent.TEXT["Q6"].format(names="th áp đang điều trị"), out["output"])
        self.assertTrue(out["needs_more"])

    def test_b13_mapped_pair_without_rule_is_stated(self):
        out = run("cần cho giảm đau (para) + kháng sinh (azithro), có tương tác gì không?",
                  planned_drugs=["para", "azithro"])
        self.assertIn(agent.TEXT["NO_PAIR_RULE"].format(
            pairs="Paracetamol (Acetaminophen) + Azithromycin"), out["output"])
        self.assertNotIn("[DDI-", out["output"])

    def test_pair_with_rule_is_not_listed_as_missing(self):
        out = run("BN đang dùng warfarin, tôi dự định kê ibuprofen.",
                  baseline_drugs=["warfarin"], planned_drugs=["ibuprofen"])
        self.assertIn("[DDI-001]", out["output"])
        self.assertNotIn("chưa có quy tắc tương tác", out["output"])

    def test_b10_case_with_ddi_rule_does_not_list_other_pairs(self):
        out = run("BN đang dùng warfarin, tôi dự định kê Alaxan.",
                  baseline_drugs=["warfarin"], planned_drugs=["ibuprofen", "paracetamol"])
        self.assertIn("[DDI-001]", out["output"])
        self.assertNotIn("chưa có quy tắc tương tác", out["output"])

    def test_b15_side_effect_question_states_limit(self):
        out = run("Tac dung phu/ chong chi dinh Methylpred 16, metronidazol 500, amox 500",
                  baseline_drugs=["Methylpred 16", "metronidazol 500", "amox 500"])
        self.assertIn(agent.TEXT["SIDE_EFFECT_LIMIT"], out["output"])
        self.assertIn(agent.TEXT["Q1"], out["output"])

    def test_no_side_effect_words_no_limit_line(self):
        out = run("BN đang dùng warfarin, tôi dự định kê ibuprofen.",
                  baseline_drugs=["warfarin"], planned_drugs=["ibuprofen"])
        self.assertNotIn("tác dụng phụ", out["output"])

    def test_b22_anesthesia_question_unchanged(self):
        out = run("BN có tiền sử dị ứng thuốc tê tại chỗ. Kế hoạch là lấy cao dưới nướu.",
                  allergies=["thuốc tê"], planned_procedures=["lấy cao dưới nướu"])
        self.assertIn(agent.TEXT["Q5"], out["output"])
        self.assertNotIn("[CR-010]", out["output"])


if __name__ == "__main__":
    unittest.main()
