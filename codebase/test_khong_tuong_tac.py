"""Ca không khớp rule nào (Trung chốt 28/11: "các ca không có tương tác ... ta phải handle trường hợp này").

1. Không có rule mà ✅ bị chặn → vẫn có dòng kết luận (bảng tra không có cảnh báo / còn câu hỏi phải trả lời).
2. ℹ️ "cặp chưa có quy tắc" không còn chặn ✅ — ✅ là kết luận, cặp chưa có quy tắc là dòng phụ.
3. BS ghi "khoẻ mạnh", "không có bệnh lý gì", "không dùng thuốc", "không dị ứng" → mục đó là "không có", không "Chưa khai".
"""
import unittest

from reply import render_chat
from test_agent_offline import run
from texts import TEXT


def X(**kw):
    d = {"conditions": [], "allergies": [], "baseline_drugs": [], "planned_procedures": [], "planned_drugs": [],
         "out_of_scope": [], "has_pii": False}
    d.update(kw)
    return d


HEALTHY_NO_MEDS = ("BN khoẻ mạnh không dùng thuốc gì. Nhổ R38. Kê Augmentin + Paracetamol",
                   X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin", "Paracetamol"]))
# Log VM 28/11 08:35 (chat nhóm): ✅ bị chặn bởi Q8 và ℹ️, không có câu kết luận, bệnh nền ghi "Chưa khai".
NO_DISEASE_LOG = ("giờ bệnh nhân không có bệnh lý gì, nhổ răng kê augmentin và paracetamol nhé",
                  X(planned_procedures=["nhổ răng"], planned_drugs=["augmentin", "paracetamol"]))


def checked(res):
    return dict(res["reply"].checked)


class KhongCoRule(unittest.TestCase):
    def test_pairs_without_rule_still_get_ok(self):
        res = run(*HEALTHY_NO_MEDS)
        reply = res["reply"]
        self.assertEqual(reply.ok, TEXT["OK"])
        self.assertIn("Amoxicillin (kể cả phối hợp clavulanate) + Paracetamol (Acetaminophen)", res["output"])
        self.assertIn(TEXT["NO_PAIR_RULE"].format(
            pairs="Amoxicillin (kể cả phối hợp clavulanate) + Paracetamol (Acetaminophen)"), reply.notes)
        self.assertEqual(reply.verdict, "")          # ✅ đã là kết luận, không lặp
        self.assertLess(res["output"].index("✅"), res["output"].index("ℹ️"))

    def test_open_question_gives_pending_verdict(self):
        res = run(*NO_DISEASE_LOG)
        reply = res["reply"]
        self.assertEqual(reply.question_key, "Q8")
        self.assertEqual(reply.ok, "")
        self.assertEqual(reply.verdict, TEXT["VERDICT_NONE_PENDING"])
        self.assertTrue(render_chat(reply).startswith(TEXT["VERDICT_NONE_PENDING"]))

    def test_unmapped_without_rule_gives_count_verdict(self):
        res = run("BN không dùng thuốc. Nhổ R38. Kê Xyzabc",
                  X(planned_procedures=["nhổ R38"], planned_drugs=["Xyzabc"]))
        reply = res["reply"]
        self.assertEqual(reply.ok, "")
        self.assertEqual(reply.verdict, TEXT["VERDICT_NONE"] + TEXT["VERDICT_NONE_UNMAPPED"].format(n=1) + ".")

    def test_refusal_without_rule_gives_plain_verdict(self):
        res = run("BN không dùng thuốc. Nhổ R38. Kê Augmentin, cho em liều luôn",
                  X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"], out_of_scope=["lieu"]))
        self.assertEqual(res["reply"].verdict, TEXT["VERDICT_NONE"] + ".")

    def test_ok_alone_has_no_verdict(self):
        res = run("Định kê ibuprofen", X(planned_drugs=["ibuprofen"]))
        self.assertEqual(res["reply"].ok, TEXT["OK"])
        self.assertEqual(res["reply"].verdict, "")

    def test_rules_keep_count_verdict(self):
        res = run("BN uống Sintrom. Nhổ R48. Định kê Ibuprofen",
                  X(baseline_drugs=["Sintrom"], planned_procedures=["nhổ R48"], planned_drugs=["Ibuprofen"]))
        self.assertTrue(res["reply"].verdict.startswith("Em rà xong rồi ạ — có "))

    def test_wording_makes_no_safety_claim(self):
        for key in ("VERDICT_NONE", "VERDICT_NONE_PENDING", "NO_PAIR_RULE"):
            folded = TEXT[key].lower()
            self.assertNotIn("an toàn", folded)
            self.assertNotIn("không có nguy cơ", folded)


class KhaiKhongCo(unittest.TestCase):
    def test_healthy_and_no_meds_are_declared_none(self):
        res = run(*HEALTHY_NO_MEDS)
        c = checked(res)
        self.assertEqual(c["Bệnh nền"], TEXT["DECLARED_NONE"])
        self.assertEqual(c["Thuốc đang dùng"], TEXT["DECLARED_NONE"])
        self.assertEqual(c["Dị ứng"], TEXT["NOT_DECLARED"])
        self.assertNotEqual(res["reply"].question_key, "Q4")
        chat = render_chat(res["reply"])
        self.assertIn("• Bệnh nền: không có", chat)
        self.assertIn("• Chưa khai: dị ứng", chat)

    def test_no_disease_phrase_from_log(self):
        c = checked(run(*NO_DISEASE_LOG))
        self.assertEqual(c["Bệnh nền"], TEXT["DECLARED_NONE"])
        self.assertEqual(c["Thuốc đang dùng"], TEXT["NOT_DECLARED"])   # "không bệnh lý" chưa nói gì về thuốc

    def test_healthy_does_not_close_q8(self):
        res = run("BN 25t khoẻ mạnh, nhổ R38, định kê Augmentin",
                  X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"]))
        self.assertEqual(res["reply"].question_key, "Q8")   # Trung chốt: "khoẻ mạnh" chưa tính là không dùng thuốc

    def test_no_allergy(self):
        for text in ("BN không dị ứng gì, không dùng thuốc. Nhổ R38. Kê Augmentin",
                     "BN ko dị ứng thuốc, không dùng thuốc. Nhổ R38. Kê Augmentin"):
            with self.subTest(text=text):
                c = checked(run(text, X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"])))
                self.assertEqual(c["Dị ứng"], TEXT["DECLARED_NONE"])

    def test_specific_negation_is_not_declared_none(self):
        # "không dị ứng thuốc tê" chỉ loại một nhóm; "không bệnh tim" chỉ loại một bệnh — chưa phải "không có".
        c = checked(run("BN không dị ứng thuốc tê, không bệnh tim. Nhổ R38. Kê Augmentin",
                        X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"])))
        self.assertEqual(c["Dị ứng"], TEXT["NOT_DECLARED"])
        self.assertEqual(c["Bệnh nền"], TEXT["NOT_DECLARED"])

    def test_narrow_or_negated_phrases_are_not_none(self):
        # Review 28/11: "không dùng thuốc chống đông" chỉ loại một nhóm thuốc; "không khoẻ mạnh" là ngược nghĩa.
        cases = {"BN không dùng thuốc chống đông. Nhổ R38. Kê Augmentin": "baseline_drugs",
                 "BN không dùng thuốc tê được. Nhổ R38. Kê Augmentin": "baseline_drugs",
                 "BN không khoẻ mạnh lắm. Nhổ R38. Kê Augmentin": "conditions",
                 "BN chưa khoẻ mạnh, nhổ R38, kê Augmentin": "conditions"}
        for text, key in cases.items():
            with self.subTest(text=text):
                self.assertNotIn(key, __import__("agent")._declared_none(text))

    def test_no_anticoagulant_still_closes_q8(self):
        # Hành vi Q8 cũ giữ nguyên: "không dùng thuốc chống đông" trả lời đúng câu Q8.
        res = run("BN không dùng thuốc chống đông. Nhổ R38. Kê Augmentin",
                  X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"]))
        self.assertNotEqual(res["reply"].question_key, "Q8")
        self.assertEqual(checked(res)["Thuốc đang dùng"], TEXT["NOT_DECLARED"])

    def test_colon_and_coordinated_forms(self):
        c = checked(run("Bệnh nền: không. Dị ứng: không. Thuốc đang dùng: không. Nhổ R38. Kê Augmentin",
                        X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"])))
        self.assertEqual({c["Bệnh nền"], c["Dị ứng"], c["Thuốc đang dùng"]}, {TEXT["DECLARED_NONE"]})
        c = checked(run("BN không bệnh lý gì và không dị ứng, nhổ R38, kê Augmentin",
                        X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"])))
        self.assertEqual((c["Bệnh nền"], c["Dị ứng"]), (TEXT["DECLARED_NONE"], TEXT["DECLARED_NONE"]))

    def test_healthy_alone_stays_no_entity(self):
        res = run("BN khoẻ mạnh", X())
        self.assertEqual(res["reply"].question_key, "Q1")
        self.assertTrue(res["reply"].is_no_entity)

    def test_none_in_merged_follow_up(self):
        import followups
        text = followups.merge("Nhổ R38. Kê Augmentin", "BN không dùng thuốc gì")
        res = run(text, X(planned_procedures=["nhổ R38"], planned_drugs=["Augmentin"]))
        self.assertEqual(checked(res)["Thuốc đang dùng"], TEXT["DECLARED_NONE"])
        self.assertNotEqual(res["reply"].question_key, "Q8")

    def test_listed_items_win_over_none_phrase(self):
        c = checked(run("BN khoẻ mạnh, chỉ có THA uống amlodipin. Nhổ R38. Kê Augmentin",
                        X(conditions=["THA"], baseline_drugs=["amlodipin"], planned_procedures=["nhổ R38"],
                          planned_drugs=["Augmentin"])))
        self.assertNotEqual(c["Bệnh nền"], TEXT["DECLARED_NONE"])
        self.assertNotEqual(c["Thuốc đang dùng"], TEXT["DECLARED_NONE"])


if __name__ == "__main__":
    unittest.main()
