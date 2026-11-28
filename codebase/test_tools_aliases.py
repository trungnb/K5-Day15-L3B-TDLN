"""Kiểm alias bổ sung 28/11/2026 (R18, R28, rung nhĩ) và rule rung nhĩ × thủ thuật chảy máu.
Chạy: cd codebase && python3 -m unittest test_tools_aliases   (không gọi model)."""
import unittest

from tools import check_clinical_risks, find_aliases, normalize_entities, normalize_text


def _ids(text):
    return {(e["canonical_id"], e["drug_class"]) for _, ents in find_aliases(normalize_text(text)) for e in ents}


class AliasAdditionsTests(unittest.TestCase):
    def test_upper_wisdom_teeth_map_to_extraction_with_both_groups(self):
        for text in ("Nhổ R18", "nho r28", "Dự kiến nhổ R18 và R28"):
            with self.subTest(text=text):
                self.assertTrue({("extraction", "invasive_bleeding"), ("extraction", "local_anesthesia")}
                                <= _ids(text))

    def test_atrial_fibrillation_is_a_condition(self):
        for text in ("BN rung nhĩ", "rung nhi", "BN RUNG NHĨ 10 năm"):
            with self.subTest(text=text):
                self.assertIn(("atrial_fibrillation", "cardiovascular"), _ids(text))

    def test_af_with_extraction_triggers_anticoagulant_question_rule(self):
        n = normalize_entities({"conditions": ["rung nhĩ"], "allergies": [], "baseline_drugs": [],
                                "planned_procedures": ["nhổ R18"], "planned_drugs": ["paracetamol"]},
                               "BN rung nhĩ. Nhổ R18, kê paracetamol")
        self.assertEqual(n["unmapped"], [])
        rules = check_clinical_risks(n["conditions"], n["allergies"], n["baseline_drugs"],
                                     n["planned_drugs"], n["procedure_groups"])
        af = [r for r in rules if "Rung nhĩ" in r["a"]]
        self.assertEqual(len(af), 1)
        self.assertEqual(af[0]["severity"], "MODERATE")
        self.assertIn("chống đông", af[0]["guidance"])


if __name__ == "__main__":
    unittest.main()
