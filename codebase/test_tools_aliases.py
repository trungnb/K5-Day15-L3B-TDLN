"""Kiểm alias bổ sung 28/11/2026 (R18, R28, rung nhĩ) và rule rung nhĩ × thủ thuật chảy máu.
Chạy: cd codebase && python3 -m unittest test_tools_aliases   (không gọi model)."""
import unittest

from tools import check_clinical_risks, check_drug_interactions, find_aliases, normalize_entities, normalize_text


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

    def test_af_abbreviation_and_english_name(self):
        # Trung duyệt 28/11/2026: "AF", "atrial fibrillation" → rung nhĩ (để CR-021 không bị bỏ sót).
        for text in ("BN AF, nhổ R48", "BN có atrial fibrillation", "tiền sử af 5 năm"):
            with self.subTest(text=text):
                self.assertIn(("atrial_fibrillation", "cardiovascular"), _ids(text))
        self.assertNotIn(("atrial_fibrillation", "cardiovascular"), _ids("BN uống Alaxan, kê Augmentin"))

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

    def test_misspelled_warfarin(self):
        # Log VM 28/11: BS gõ "wafarin" → bot không nhận ra, mất cảnh báo warfarin + nhổ răng / ibuprofen.
        self.assertIn(("warfarin", "vka"), _ids("BN đang uống wafarin. Dự kiến nhổ răng khôn."))

    def test_other_names_of_known_procedures(self):
        cases = {"tooth extraction": ("extraction", "invasive_bleeding"), "Chích áp xe": ("abscess_drainage",
                 "invasive_bleeding"), "dẫn lưu áp xe": ("abscess_drainage", "invasive_bleeding"),
                 "điều trị tủy R46": ("non_invasive_dental", "non_invasive")}
        for text, key in cases.items():
            with self.subTest(text=text):
                self.assertIn(key, _ids(text))

    def test_abscess_and_pulp_procedures_carry_local_anesthesia(self):
        # Trung chốt 28/11/2026 (câu hỏi review PR #30 của Nguyên): áp xe và điều trị tủy thường có gây tê.
        cases = {"chích áp xe": "abscess_drainage", "trích áp xe": "abscess_drainage",
                 "dẫn lưu áp xe": "abscess_drainage", "rạch áp xe": "abscess_drainage",
                 "điều trị tủy R46": "non_invasive_dental", "lấy tủy R36": "non_invasive_dental",
                 "điều trị nội nha": "non_invasive_dental", "chữa tủy": "non_invasive_dental",
                 "nội nha R26": "non_invasive_dental"}
        for text, cid in cases.items():
            with self.subTest(text=text):
                self.assertIn((cid, "local_anesthesia"), _ids(text))
        for text in ("trám răng", "khám răng", "lấy cao răng trên nướu"):   # không tự kéo theo gây tê
            with self.subTest(text=text):
                self.assertNotIn(("non_invasive_dental", "local_anesthesia"), _ids(text))

    def test_anesthetic_allergy_with_abscess_drainage_warns_directly(self):
        n = normalize_entities({"conditions": [], "allergies": ["thuốc tê"], "baseline_drugs": [],
                                "planned_procedures": ["chích áp xe"], "planned_drugs": []},
                               "BN dị ứng thuốc tê. Chích áp xe")
        rules = check_clinical_risks(n["conditions"], n["allergies"], n["baseline_drugs"],
                                     n["planned_drugs"], n["procedure_groups"])
        self.assertIn("CR-010", {r["rule_id"] for r in rules})

    def test_proposed_rows_do_not_borrow_reviewed_sources(self):
        import csv
        from pathlib import Path
        rows = csv.DictReader((Path(__file__).resolve().parents[1] / "data" / "entity_aliases.csv")
                              .open(encoding="utf-8-sig"))
        for row in rows:
            # Gồm cả dòng local_anesthesia sinh kèm cho "extraction" / "tooth extraction" (review PR #30).
            if row["alias"] in {"ibu", "metro", "chich ap xe", "dieu tri tuy", "extraction", "tooth extraction", "af", "atrial fibrillation", "wafarin",
                                "chong dong", "thuoc chong dong", "khang dong", "thuoc khang dong", "loang mau",
                                "thuoc loang mau", "khang tieu cau", "thuoc khang tieu cau", "chong ket tap tieu cau",
                                "thuoc chong ket tap tieu cau"}:
                # Dòng gây tê của áp xe / điều trị tủy ghi "Trung chốt 28/11/2026" (phân nhóm), không mượn nguồn 27/11.
                expected = "Trung chốt 28/11/2026" if row["drug_class"] == "local_anesthesia" and row["canonical_id"] != "extraction" \
                    else "Trung duyệt 28/11/2026"
                self.assertIn(expected, row["source"], row["alias"])


class ToothNumberTests(unittest.TestCase):
    def test_any_tooth_number_after_nho_maps_to_extraction(self):
        # Tự thử 28/11/2026: "nhổ R36" không khớp alias nào (chỉ có R8/R18–R48) → mất CR-001 khi BN uống warfarin.
        for text in ("Nhổ R36", "nhổ R46 viêm", "Dự kiến nhổ r11", "nho R 36", "Nhổ R48"):
            with self.subTest(text=text):
                self.assertIn(("extraction", "invasive_bleeding"), _ids(text))

    def test_tooth_number_phrase_from_model_is_mapped_and_triggers_cr001(self):
        n = normalize_entities({"conditions": [], "allergies": [], "baseline_drugs": ["warfarin"],
                                "planned_procedures": ["nhổ R36"], "planned_drugs": []},
                               "BN uống warfarin, nhổ R36")
        self.assertEqual(n["unmapped"], [])
        rules = check_clinical_risks(n["conditions"], n["allergies"], n["baseline_drugs"],
                                     n["planned_drugs"], n["procedure_groups"])
        self.assertIn("CR-001", {r["rule_id"] for r in rules})

    def test_numbers_in_drug_aliases_still_match(self):
        self.assertIn(("aspirin", normalize_entities({"baseline_drugs": ["aspirin 81"]}, "aspirin 81")
                       ["baseline_drugs"][0]["drug_class"]), _ids("BN uống aspirin 81"))


class OutsideTesterAliasTests(unittest.TestCase):
    """BS ngoài nhóm 28/11/2026 (validation/log.md): "vigentin", "amlodipin", "cao huyết áp" chưa nhận ra.
    Trung (BS RHM) yêu cầu thêm 28/11/2026."""

    def test_vigentin_is_amoxicillin(self):
        for text in ("kê vigentin", "Kê đơn: Vigentin 625"):
            with self.subTest(text=text):
                self.assertIn(("amoxicillin", "penicillin"), _ids(text))

    def test_amlodipine_spellings_are_a_drug(self):
        for text in ("Bn sử dụng amlodipin", "đang uống amlodipine 5mg", "uống Amlor"):
            with self.subTest(text=text):
                self.assertIn(("amlodipine", "ccb"), _ids(text))

    def test_cao_huyet_ap_chua_kiem_soat_is_uncontrolled_hypertension(self):
        self.assertIn(("uncontrolled_hypertension", "cardiovascular"), _ids("BN cao huyết áp chưa kiểm soát"))

    def test_outside_case_now_maps_all_drugs(self):
        text = "Bn 65t sử dụng amlodipin  cao huyết áp. Dự kiến điều trị tuỷ r16 gây tê bằng lidocain. Kê đơn: vigentin + paracetamol"
        n = normalize_entities({"conditions": [], "allergies": [], "baseline_drugs": ["amlodipin"],
                                "planned_procedures": ["điều trị tuỷ r16"],
                                "planned_drugs": ["lidocain", "vigentin", "paracetamol"]}, text)
        self.assertEqual({d["canonical_id"] for d in n["baseline_drugs"]}, {"amlodipine"})
        self.assertIn("amoxicillin", {d["canonical_id"] for d in n["planned_drugs"]})

    def test_amlodipine_with_nsaid_or_macrolide_is_moderate(self):
        for drug in ("ibuprofen", "clarithromycin"):
            with self.subTest(drug=drug):
                n = normalize_entities({"baseline_drugs": ["amlodipin"], "planned_drugs": [drug]},
                                       f"uống amlodipin, kê {drug}")
                hits = check_drug_interactions(n["baseline_drugs"], n["planned_drugs"])
                self.assertEqual([r["severity"] for r in hits], ["MODERATE"])


if __name__ == "__main__":
    unittest.main()


class NearMatch2811(unittest.TestCase):
    """So gần đúng chỉ dùng cho chữ không khớp alias nào, chỉ trong đúng loại thực thể của danh sách model trả."""

    def test_near_match_only_within_list_type(self):
        n = normalize_entities({"conditions": [], "allergies": ["peniciline"], "baseline_drugs": [],
                                "planned_procedures": [], "planned_drugs": []}, "")
        self.assertEqual([e["canonical_id"] for e in n["allergies"]], ["penicillin"])
        self.assertEqual(n["unmapped"], [])
        self.assertEqual(n["near_matches"][0][0], "peniciline")

    def test_exact_alias_does_not_report_near_match(self):
        n = normalize_entities({"conditions": [], "allergies": ["penicillin"], "baseline_drugs": [],
                                "planned_procedures": [], "planned_drugs": []}, "")
        self.assertEqual(n["near_matches"], [])
