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


class AliasProposals2811Tests(unittest.TestCase):
    """Rà UX 28/11: viết tắt / cách gọi khác của thực thể ĐÃ có (không thêm quy tắc mới)."""

    def test_short_drug_names(self):
        self.assertIn(("ibuprofen", "nsaid"), _ids("kê ibu"))
        self.assertIn(("metronidazole", "nitroimidazole"), _ids("kê metro"))

    def test_other_names_of_known_procedures(self):
        cases = {"tooth extraction": ("extraction", "invasive_bleeding"), "Chích áp xe": ("abscess_drainage",
                 "invasive_bleeding"), "dẫn lưu áp xe": ("abscess_drainage", "invasive_bleeding"),
                 "điều trị tủy R46": ("non_invasive_dental", "non_invasive")}
        for text, key in cases.items():
            with self.subTest(text=text):
                self.assertIn(key, _ids(text))

    def test_proposed_rows_do_not_borrow_reviewed_sources(self):
        import csv
        from pathlib import Path
        rows = csv.DictReader((Path(__file__).resolve().parents[1] / "data" / "entity_aliases.csv")
                              .open(encoding="utf-8-sig"))
        for row in rows:
            if row["alias"] in {"ibu", "metro", "chich ap xe", "dieu tri tuy"}:
                self.assertIn("CHỜ BS RHM duyệt", row["source"], row["alias"])


if __name__ == "__main__":
    unittest.main()
