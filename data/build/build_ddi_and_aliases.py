"""Sinh tất định data/entity_aliases.csv và data/ddi_rules.csv từ data/raw/ddinter/ + QĐ 5948.

Mọi cặp có đối chiếu DDInter đều được assert trực tiếp vào các file CSV trong data/raw/ddinter/.
Chỉ dùng thư viện chuẩn Python. Chạy từ thư mục gốc repo:
    python3 data/build/build_ddi_and_aliases.py
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DDINTER_DIR = DATA_DIR / "raw" / "ddinter"

ALIAS_COLS = ["alias", "canonical_id", "display_name", "entity_type", "drug_class", "notes", "source"]
DDI_COLS = ["rule_id", "drug_a", "drug_b", "severity", "mechanism", "clinical_guidance", "source"]


def load_ddinter() -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    ids: dict[str, str] = {}
    pairs: dict[tuple[str, str], str] = {}
    csv_files = sorted(DDINTER_DIR.glob("ddinter_downloads_code_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Không tìm thấy file DDInter CSV trong {DDINTER_DIR}")

    for path in csv_files:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                da = row["Drug_A"].strip().lower()
                db = row["Drug_B"].strip().lower()
                lvl = row["Level"].strip()
                ids[da] = row["DDInterID_A"].strip()
                ids[db] = row["DDInterID_B"].strip()
                if lvl not in ("Major", "Moderate", "Minor"):
                    continue
                k = tuple(sorted((da, db)))
                if k not in pairs or (pairs[k] != "Major" and lvl == "Major"):
                    pairs[k] = lvl
    return ids, pairs


COMBO_NOTES: dict[str, str] = {
    "alaxan": "combo:ibuprofen+paracetamol",
    "coplavix": "combo:clopidogrel+aspirin",
    "rodogyl": "combo:spiramycin+metronidazole",
    "dorogyne": "combo:spiramycin+metronidazole",
    "naphacogyl": "combo:spiramycin+metronidazole",
    "vimovo": "combo:naproxen+esomeprazole",
    "fortzaar": "combo:losartan+hydrochlorothiazide",
    "lignospan": "combo:lidocaine+epinephrine (thuốc tê có co mạch)",
    "septanest": "combo:articaine+epinephrine (thuốc tê có co mạch)",
    "ubistesin": "combo:articaine+epinephrine (thuốc tê có co mạch)",
}


def build_alias_rows(ddinter_ids: dict[str, str]) -> list[dict[str, str]]:
    # (canonical_id, display_name, entity_type, drug_class, ddinter_lookup, source, aliases)
    specs: list[tuple[str, str, str, str, str | None, str, list[str]]] = [
        # --- Thuốc định kê RHM cốt lõi ---
        (
            "amoxicillin",
            "Amoxicillin (kể cả phối hợp clavulanate)",
            "drug",
            "penicillin",
            "amoxicillin",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            [
                "amoxicillin",
                "amox",
                "amoxicilin",
                "augmentin",
                "clamoxyl",
                "amoxicillin clavulanate",
                "klamentin",
                "claminat",
                "curam",
                "amoksiklav",
                "augbactam",
                "hiconcil",
            ],
        ),
        (
            "metronidazole",
            "Metronidazole",
            "drug",
            "nitroimidazole",
            "metronidazole",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["metronidazole", "metronidazol", "flagyl", "klion", "rodogyl", "medazol", "dorogyne", "naphacogyl"],
        ),
        (
            "clindamycin",
            "Clindamycin",
            "drug",
            "lincosamide",
            "clindamycin",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["clindamycin", "dalacin c"],
        ),
        (
            "azithromycin",
            "Azithromycin",
            "drug",
            "macrolide_azithromycin",
            "azithromycin",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["azithromycin", "zithromax", "azi", "zaromax", "azicine", "azimycin", "zitromax"],
        ),
        (
            "clarithromycin",
            "Clarithromycin",
            "drug",
            "macrolide_cyp3a4",
            "clarithromycin",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["clarithromycin", "klacid", "fromilid", "zenclar"],
        ),
        (
            "erythromycin",
            "Erythromycin",
            "drug",
            "macrolide_cyp3a4",
            "erythromycin",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["erythromycin", "ery"],
        ),
        (
            "ibuprofen",
            "Ibuprofen",
            "drug",
            "nsaid",
            "ibuprofen",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["ibuprofen", "brufen", "gofen", "alaxan", "nurofen", "ibumed"],
        ),
        (
            "naproxen",
            "Naproxen",
            "drug",
            "nsaid",
            "naproxen",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["naproxen", "naprosyn", "vimovo", "proxen"],
        ),
        (
            "meloxicam",
            "Meloxicam",
            "drug",
            "nsaid",
            "meloxicam",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["meloxicam", "mobic", "meloflam"],
        ),
        (
            "diclofenac",
            "Diclofenac",
            "drug",
            "nsaid",
            "diclofenac",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["diclofenac", "voltaren", "cataflam"],
        ),
        (
            "ketorolac",
            "Ketorolac",
            "drug",
            "nsaid",
            "ketorolac",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["ketorolac", "toradol", "ketorolac tromethamin"],
        ),
        (
            "celecoxib",
            "Celecoxib",
            "drug",
            "nsaid_cox2",
            "celecoxib",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["celecoxib", "celebrex"],
        ),
        (
            "acetaminophen",
            "Paracetamol (Acetaminophen)",
            "drug",
            "analgesic",
            "acetaminophen",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["paracetamol", "acetaminophen", "efferalgan", "hapacol", "panadol", "para", "partamol", "tylenol"],
        ),
        (
            "dexamethasone",
            "Dexamethasone",
            "drug",
            "corticosteroid",
            "dexamethasone",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["dexamethasone", "dexamethason", "dexa", "decadron", "fortec"],
        ),
        (
            "prednisolone",
            "Prednisolone",
            "drug",
            "corticosteroid",
            "prednisolone",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["prednisolone", "prednisolon", "solupred", "mecpred", "solpred"],
        ),
        (
            "methylprednisolone",
            "Methylprednisolone",
            "drug",
            "corticosteroid",
            "methylprednisolone",
            "DDInter; biệt dược phổ biến tại VN (BS RHM duyệt 27/11/2026)",
            ["methylprednisolone", "medrol", "menison", "solu-medrol"],
        ),
        (
            "lidocaine",
            "Lidocaine",
            "drug",
            "local_anesthetic",
            "lidocaine",
            "DDInter; thực hành RHM (BS RHM duyệt 27/11/2026)",
            ["lidocaine", "lidocain", "xylocaine"],
        ),
        (
            "epinephrine",
            "Epinephrine (Adrenaline)",
            "drug",
            "vasoconstrictor",
            "epinephrine",
            "DDInter; QĐ 5948/QĐ-BYT (2021) (BS RHM duyệt 27/11/2026)",
            ["epinephrine", "adrenaline", "adrenalin", "thuoc co mach", "lignospan", "septanest", "ubistesin"],
        ),
        (
            "mepivacaine",
            "Mepivacaine 3% Plain (Scandonest — thuốc tê không co mạch)",
            "drug",
            "local_anesthetic",
            "mepivacaine",
            "DDInter; vật liệu/thuốc tê RHM lưu hành tại VN (BS RHM duyệt 27/11/2026)",
            ["mepivacaine", "mepivacain", "scandonest"],
        ),
        (
            "articaine",
            "Articaine (thuốc tê nha khoa)",
            "drug",
            "local_anesthetic",
            "articaine",
            "DDInter; vật liệu/thuốc tê RHM lưu hành tại VN (BS RHM duyệt 27/11/2026)",
            ["articaine", "articain"],
        ),
        # --- Thuốc nền thường gặp ở BN RHM ---
        (
            "warfarin",
            "Warfarin (kháng vitamin K)",
            "drug",
            "vka",
            "warfarin",
            "DDInter; SDCEP QRG (2022), p. 4; QĐ 5948/QĐ-BYT (2021), tr. 169",
            ["warfarin"],
        ),
        (
            "acenocoumarol",
            "Acenocoumarol (Sintrom — kháng vitamin K)",
            "drug",
            "vka",
            "acenocoumarol",
            "DDInter; SDCEP QRG (2022), p. 4; QĐ 5948/QĐ-BYT (2021), tr. 169",
            ["acenocoumarol", "sintrom", "minisintrom"],
        ),
        (
            "rivaroxaban",
            "Rivaroxaban (Xarelto — DOAC)",
            "drug",
            "doac",
            "rivaroxaban",
            "DDInter; SDCEP QRG (2022), p. 3",
            ["rivaroxaban", "xarelto"],
        ),
        (
            "apixaban",
            "Apixaban (Eliquis — DOAC)",
            "drug",
            "doac",
            "apixaban",
            "DDInter; SDCEP QRG (2022), p. 3",
            ["apixaban", "eliquis"],
        ),
        (
            "dabigatran",
            "Dabigatran (Pradaxa — DOAC)",
            "drug",
            "doac",
            None,
            "SDCEP QRG (2022), p. 3; QĐ 5948/QĐ-BYT (2021), Phần 2 STT 59 tr. 173 [ghi chú: thiếu trong 8 file CSV DDInter tải về]",
            ["dabigatran", "pradaxa"],
        ),
        (
            "enoxaparin",
            "Enoxaparin (Lovenox — LMWH)",
            "drug",
            "lmwh",
            "enoxaparin",
            "DDInter; SDCEP QRG (2022), p. 4",
            ["enoxaparin", "lovenox"],
        ),
        (
            "clopidogrel",
            "Clopidogrel (Plavix — kháng tiểu cầu P2Y12)",
            "drug",
            "p2y12_antiplatelet",
            "clopidogrel",
            "DDInter; SDCEP QRG (2022), p. 5",
            ["clopidogrel", "plavix", "clopistad", "clopilet", "coplavix"],
        ),
        (
            "ticagrelor",
            "Ticagrelor (Brilinta — kháng tiểu cầu P2Y12)",
            "drug",
            "p2y12_antiplatelet",
            "ticagrelor",
            "DDInter; SDCEP QRG (2022), p. 5; QĐ 5948/QĐ-BYT (2021), tr. 52",
            ["ticagrelor", "brilinta"],
        ),
        (
            "aspirin",
            "Aspirin (Acetylsalicylic acid)",
            "drug",
            "antiplatelet",
            "acetylsalicylic acid",
            "DDInter (Acetylsalicylic acid); SDCEP QRG (2022), p. 5",
            [
                "aspirin",
                "acetylsalicylic acid",
                "aspilets",
                "aspirin 81",
                "aspirin ph8",
                "kardegic",
                "cardioaspirin",
                "aspegic",
            ],
        ),
        (
            "alendronic acid",
            "Alendronate / Alendronic acid (Fosamax — Bisphosphonate)",
            "drug",
            "bisphosphonate",
            "alendronic acid",
            "DDInter; AAOMS MRONJ (2022), PMID 35300956",
            ["alendronic acid", "alendronate", "fosamax", "bisphosphonate", "alenta", "alenbe", "aronat"],
        ),
        (
            "zoledronic acid",
            "Zoledronic acid (Aclasta / Zometa — Bisphosphonate IV)",
            "drug",
            "bisphosphonate",
            "zoledronic acid",
            "DDInter; AAOMS MRONJ (2022), PMID 35300956",
            ["zoledronic acid", "zoledronate", "aclasta", "zometa", "zoled", "zoltonar"],
        ),
        (
            "denosumab",
            "Denosumab (Prolia / Xgeva — ức chế RANKL)",
            "drug",
            "rankl_inhibitor",
            "denosumab",
            "DDInter; AAOMS MRONJ (2022), PMID 35300956",
            ["denosumab", "prolia", "xgeva"],
        ),
        (
            "simvastatin",
            "Simvastatin (Statin CYP3A4)",
            "drug",
            "statin_cyp3a4",
            "simvastatin",
            "DDInter; QĐ 5948/QĐ-BYT (2021), tr. 50, 83, 161",
            ["simvastatin", "zocor"],
        ),
        (
            "atorvastatin",
            "Atorvastatin (Lipitor)",
            "drug",
            "statin_cyp3a4",
            "atorvastatin",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["atorvastatin", "lipitor", "atoris", "totalstat"],
        ),
        (
            "amiodarone",
            "Amiodarone (Cordarone — chống loạn nhịp)",
            "drug",
            "antiarrhythmic_qt",
            "amiodarone",
            "DDInter; QĐ 5948/QĐ-BYT (2021), tr. 22–25, 165",
            ["amiodarone", "amiodaron", "cordarone"],
        ),
        (
            "colchicine",
            "Colchicine (điều trị Gout)",
            "drug",
            "antigout",
            "colchicine",
            "DDInter; QĐ 5948/QĐ-BYT (2021), tr. 51",
            ["colchicine", "colchicin"],
        ),
        (
            "carbamazepine",
            "Carbamazepine (Tegretol)",
            "drug",
            "anticonvulsant",
            "carbamazepine",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["carbamazepine", "tegretol"],
        ),
        (
            "cyclosporine",
            "Cyclosporine (ức chế miễn dịch)",
            "drug",
            "immunosuppressant",
            "cyclosporine",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["cyclosporine", "ciclosporin", "sandimmun", "neoral"],
        ),
        (
            "digoxin",
            "Digoxin",
            "drug",
            "cardiac_glycoside",
            "digoxin",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["digoxin"],
        ),
        (
            "propranolol",
            "Propranolol (chẹn beta không chọn lọc)",
            "drug",
            "beta_blocker_nonselective",
            "propranolol",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["propranolol", "dorocardyl", "inderal"],
        ),
        (
            "methotrexate",
            "Methotrexate",
            "drug",
            "dmard",
            "methotrexate",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["methotrexate", "mtx", "metoject"],
        ),
        (
            "enalapril",
            "Enalapril (ức chế men chuyển)",
            "drug",
            "acei",
            "enalapril",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["enalapril", "renitec", "ednyt"],
        ),
        (
            "losartan",
            "Losartan (chẹn thụ thể angiotensin)",
            "drug",
            "arb",
            "losartan",
            "DDInter (BS RHM duyệt 27/11/2026)",
            ["losartan", "cozaar", "fortzaar", "lozar"],
        ),
        (
            "metformin",
            "Metformin (Glucophage — ĐTĐ type 2)",
            "drug",
            "biguanide",
            "metformin",
            "DDInter; thực hành RHM (BS RHM duyệt 27/11/2026)",
            ["metformin", "glucophage", "siofor", "glucophage xr", "glucofast"],
        ),
        # --- Dị ứng (luôn bắt đầu bằng 'di ung ...' để không trùng tên thuốc) ---
        (
            "penicillin",
            "Dị ứng Penicillin / Beta-lactam",
            "allergy",
            "allergy_beta_lactam",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["di ung penicillin", "di ung penicilin", "di ung amoxicillin", "di ung augmentin", "di ung beta-lactam"],
        ),
        (
            "nsaid",
            "Dị ứng NSAID / Aspirin",
            "allergy",
            "allergy_nsaid",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["di ung nsaid", "di ung ibuprofen", "di ung giam dau", "di ung aspirin"],
        ),
        (
            "local_anesthetic",
            "Dị ứng thuốc tê nha khoa",
            "allergy",
            "allergy_anesthetic",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["di ung thuoc te", "di ung lidocain", "di ung lidocaine"],
        ),
        # --- Bệnh nền ---
        (
            "peptic_ulcer",
            "Loét dạ dày tá tràng / Xuất huyết tiêu hoá",
            "condition",
            "gi_risk",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["loet da day", "viem loet da day", "loet da day ta trang", "loet ta trang", "xuat huyet tieu hoa", "xhth"],
        ),
        (
            "ckd",
            "Bệnh thận mạn / Suy thận",
            "condition",
            "renal_impairment",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["suy than", "benh than man", "ckd"],
        ),
        (
            "pregnancy",
            "Đang mang thai / Thai kỳ",
            "condition",
            "pregnancy",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["mang thai", "co thai", "thai ky", "bau"],
        ),
        (
            "uncontrolled_hypertension",
            "Tăng huyết áp chưa kiểm soát",
            "condition",
            "cardiovascular",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            [
                "tang huyet ap chua kiem soat",
                "huyet ap cao chua kiem soat",
                "tha chua kiem soat",
                "huyet ap chua on dinh",
                "ha chua kiem soat",
                "con tang huyet ap",
            ],
        ),
        (
            "diabetes",
            "Đái tháo đường",
            "condition",
            "metabolic",
            None,
            "Từ điển thực thể RHM nhóm TDLN (BS RHM duyệt 27/11/2026)",
            ["dai thao duong", "tieu duong", "dtd", "dtd2", "dtd type 2"],
        ),
        (
            "bleeding_disorder",
            "Rối loạn đông máu / Giảm tiểu cầu / Xơ gan nặng",
            "condition",
            "coagulopathy",
            None,
            "SDCEP QRG (2022), p. 1–2 (BS RHM duyệt 27/11/2026)",
            ["roi loan dong mau", "hemophilia", "giam tieu cau", "xuat huyet giam tieu cau"],
        ),
        # --- Thủ thuật RHM ---
        (
            "extraction",
            "Nhổ răng / Tiểu phẫu răng khôn",
            "procedure",
            "invasive_bleeding",
            None,
            "SDCEP QRG (2022), Table 1 p. 3",
            ["nho rang", "nho r", "nho r8", "nho r48", "nho r38", "nho rang khon", "tieu phau"],
        ),
        (
            "implant_surgery",
            "Cấy ghép Implant / Phẫu thuật nha chu / Tạo vạt",
            "procedure",
            "invasive_bleeding",
            None,
            "SDCEP QRG (2022), Table 1 p. 3",
            ["implant", "cay implant", "phau thuat nha chu", "tao vat", "rach ap xe", "lay cao duoi nuou"],
        ),
        (
            "local_anesthesia_proc",
            "Gây tê nha khoa (có thuốc co mạch)",
            "procedure",
            "local_anesthesia",
            None,
            "SDCEP QRG (2022), Table 1 p. 3; thực hành RHM (BS RHM duyệt 27/11/2026)",
            ["gay te", "gay te vung", "tiem te"],
        ),
        (
            "non_invasive_dental",
            "Khám / Trám răng đơn giản / Nội nha / Lấy cao trên nướu",
            "procedure",
            "non_invasive",
            None,
            "SDCEP QRG (2022), Table 1 p. 3",
            ["tram rang", "noi nha", "chua tuy", "lay cao rang tren nuou", "kham rang"],
        ),
    ]

    rows: list[dict[str, str]] = []
    for canonical_id, display_name, entity_type, drug_class, dd_key, source, aliases in specs:
        if dd_key is not None:
            dd_id = ddinter_ids.get(dd_key, "")
            if not dd_id:
                raise AssertionError(f"Thiếu {dd_key!r} trong DDInter CSV")
            notes = f"DDInterID:{dd_id}"
        elif canonical_id == "dabigatran":
            notes = "unmapped_ddinter"
        else:
            notes = ""
        for alias in aliases:
            combo = COMBO_NOTES.get(alias, "")
            row_notes = f"{notes}; {combo}" if (notes and combo) else (notes or combo)
            rows.append(
                {
                    "alias": alias,
                    "canonical_id": canonical_id,
                    "display_name": display_name,
                    "entity_type": entity_type,
                    "drug_class": drug_class,
                    "notes": row_notes,
                    "source": source,
                }
            )
    return rows


def build_ddi_rows(ddinter_pairs: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    # Mỗi mục có ddinter_checks (list[(drug_a, drug_b, expected_level)]) sẽ được assert trực tiếp trên DDInter CSV.
    rules: list[dict[str, Any]] = [
        # --- HIGH: Chống đông + Giảm đau/Kháng sinh RHM ---
        {
            "rule_id": "DDI-001",
            "drug_a": "class:nsaid",
            "drug_b": "class:vka",
            "severity": "HIGH",
            "mechanism": "NSAID ức chế kết tập tiểu cầu, kích ứng niêm mạc tiêu hoá và cạnh tranh gắn protein/chuyển hoá, làm tăng rõ rệt nguy cơ xuất huyết nặng (đặc biệt xuất huyết tiêu hoá) khi dùng cùng kháng vitamin K.",
            "clinical_guidance": "Tránh phối hợp NSAID toàn thân với thuốc kháng vitamin K (warfarin/acenocoumarol); để BS cân nhắc lựa chọn giảm đau không làm tăng nguy cơ chảy máu và theo dõi sát dấu hiệu xuất huyết/INR nếu đã lỡ dùng.",
            "source": "DDInter (Major: Warfarin + Ibuprofen/Naproxen/Meloxicam/Diclofenac/Ketorolac); nhóm VKA theo QĐ 5948/QĐ-BYT (2021), Phần 2 STT 43 tr. 169 (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("warfarin", "ibuprofen", "Major"),
                ("warfarin", "naproxen", "Major"),
                ("warfarin", "meloxicam", "Major"),
                ("warfarin", "diclofenac", "Major"),
                ("warfarin", "ketorolac", "Major"),
            ],
        },
        {
            "rule_id": "DDI-002",
            "drug_a": "class:nsaid",
            "drug_b": "class:doac",
            "severity": "HIGH",
            "mechanism": "Phối hợp NSAID với thuốc chống đông đường uống trực tiếp (rivaroxaban, apixaban, dabigatran) làm hiệp đồng tăng nguy cơ chảy máu đường tiêu hoá và xuất huyết toàn thân.",
            "clinical_guidance": "Tránh phối hợp NSAID thường quy với DOAC; để BS cân nhắc hướng giảm đau thay thế ít nguy cơ chảy máu hơn và dặn BN theo dõi dấu hiệu xuất huyết (bầm tím bất thường, phân đen, chảy máu chân răng kéo dài).",
            "source": "DDInter (Major: Rivaroxaban/Apixaban + Ibuprofen/Naproxen/Meloxicam/Diclofenac/Ketorolac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("rivaroxaban", "ibuprofen", "Major"),
                ("rivaroxaban", "naproxen", "Major"),
                ("rivaroxaban", "meloxicam", "Major"),
                ("rivaroxaban", "diclofenac", "Major"),
                ("rivaroxaban", "ketorolac", "Major"),
                ("apixaban", "ibuprofen", "Major"),
                ("apixaban", "naproxen", "Major"),
                ("apixaban", "meloxicam", "Major"),
                ("apixaban", "diclofenac", "Major"),
                ("apixaban", "ketorolac", "Major"),
            ],
        },
        {
            "rule_id": "DDI-003",
            "drug_a": "class:nsaid",
            "drug_b": "class:lmwh",
            "severity": "HIGH",
            "mechanism": "NSAID ức chế chức năng tiểu cầu và tăng tổn thương niêm mạc dạ dày, hiệp đồng làm tăng nguy cơ xuất huyết khi dùng đồng thời với heparin trọng lượng phân tử thấp (enoxaparin).",
            "clinical_guidance": "Tránh phối hợp NSAID với LMWH nếu không có chỉ định và theo dõi chuyên khoa; để BS cân nhắc lựa chọn giảm đau an toàn hơn.",
            "source": "DDInter (Major: Enoxaparin + Ibuprofen/Naproxen/Meloxicam/Diclofenac/Ketorolac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("enoxaparin", "ibuprofen", "Major"),
                ("enoxaparin", "naproxen", "Major"),
                ("enoxaparin", "meloxicam", "Major"),
                ("enoxaparin", "diclofenac", "Major"),
                ("enoxaparin", "ketorolac", "Major"),
            ],
        },
        {
            "rule_id": "DDI-004",
            "drug_a": "ibuprofen",
            "drug_b": "aspirin",
            "severity": "HIGH",
            "mechanism": "Ibuprofen cạnh tranh vị trí gắn COX-1 trên tiểu cầu làm giảm tác dụng chống kết tập tiểu cầu bảo vệ tim mạch của aspirin liều thấp, đồng thời tăng nguy cơ kích ứng/xuất huyết tiêu hoá.",
            "clinical_guidance": "Thận trọng tối đa / tránh dùng ibuprofen kéo dài ở BN đang dùng aspirin bảo vệ tim mạch; để BS cân nhắc hướng giảm đau khác không cản trở tác dụng chống kết tập tiểu cầu của aspirin.",
            "source": "DDInter (Major: Acetylsalicylic acid + Ibuprofen) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("acetylsalicylic acid", "ibuprofen", "Major")],
        },
        {
            "rule_id": "DDI-005",
            "drug_a": "ketorolac",
            "drug_b": "aspirin",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng ức chế tổng hợp prostaglandin và kích ứng niêm mạc dạ dày, làm tăng rất cao nguy cơ loét và xuất huyết tiêu hoá nghiêm trọng.",
            "clinical_guidance": "Chống chỉ định / tránh phối hợp ketorolac với aspirin hoặc NSAID khác; để BS điều chỉnh đơn giảm đau.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 85 tr. 30 & Phần 2 STT 7 tr. 158; DDInter (Major: Acetylsalicylic acid + Ketorolac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("acetylsalicylic acid", "ketorolac", "Major")],
        },
        {
            "rule_id": "DDI-006",
            "drug_a": "ibuprofen",
            "drug_b": "ketorolac",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng tác dụng ức chế COX và kích ứng đường tiêu hoá khi phối hợp hai NSAID.",
            "clinical_guidance": "Chống chỉ định phối hợp đồng thời hai thuốc nhóm NSAID (ketorolac + ibuprofen); chỉ giữ một hướng giảm đau theo chỉ định BS.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 425 tr. 106 & Phần 2 STT 7 tr. 158; DDInter (Major: Ibuprofen + Ketorolac)",
            "ddinter_checks": [("ibuprofen", "ketorolac", "Major")],
        },
        {
            "rule_id": "DDI-007",
            "drug_a": "diclofenac",
            "drug_b": "ketorolac",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng tác dụng kích ứng đường tiêu hoá và nguy cơ suy thận khi dùng đồng thời hai NSAID.",
            "clinical_guidance": "Chống chỉ định phối hợp ketorolac và diclofenac.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 266 tr. 70 & Phần 2 STT 7 tr. 158; DDInter (Major: Diclofenac + Ketorolac)",
            "ddinter_checks": [("diclofenac", "ketorolac", "Major")],
        },
        {
            "rule_id": "DDI-008",
            "drug_a": "meloxicam",
            "drug_b": "ketorolac",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng tác dụng kích ứng đường tiêu hoá, tăng nguy cơ xuất huyết tiêu hoá nghiêm trọng.",
            "clinical_guidance": "Chống chỉ định phối hợp ketorolac và meloxicam.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 480 tr. 122 & Phần 2 STT 7 tr. 158",
            "ddinter_checks": [],
        },
        {
            "rule_id": "DDI-009",
            "drug_a": "metronidazole",
            "drug_b": "class:vka",
            "severity": "HIGH",
            "mechanism": "Metronidazole ức chế chuyển hoá đồng phân S-warfarin (và các dẫn chất kháng vitamin K) qua CYP2C9, làm tăng mạnh tác dụng chống đông và tăng INR.",
            "clinical_guidance": "Tránh kê metronidazole ở BN đang dùng kháng vitamin K nếu có lựa chọn phù hợp khác; nếu bắt buộc dùng, phải báo và phối hợp BS điều trị theo dõi sát INR để tránh xuất huyết.",
            "source": "DDInter (Major: Metronidazole + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("metronidazole", "warfarin", "Major")],
        },
        # --- HIGH: Macrolide CYP3A4 (Clarithromycin / Erythromycin) ---
        {
            "rule_id": "DDI-010",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "simvastatin",
            "severity": "HIGH",
            "mechanism": "Clarithromycin và erythromycin ức chế mạnh enzym CYP3A4, làm tăng mạnh nồng độ simvastatin huyết thanh và nguy cơ bệnh cơ / tiêu cơ vân cấp.",
            "clinical_guidance": "Chống chỉ định phối hợp clarithromycin hoặc erythromycin với simvastatin; để BS chọn kháng sinh không ức chế CYP3A4 hoặc hội chẩn BS tim mạch nếu bắt buộc dùng.",
            "source": "QĐ 5948/QĐ-BYT (2021), tr. 50, 83 & Phần 2 STT 16 tr. 161; DDInter (Major)",
            "ddinter_checks": [
                ("clarithromycin", "simvastatin", "Major"),
                ("erythromycin", "simvastatin", "Major"),
            ],
        },
        {
            "rule_id": "DDI-011",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "atorvastatin",
            "severity": "HIGH",
            "mechanism": "Clarithromycin và erythromycin ức chế chuyển hoá atorvastatin qua CYP3A4, làm tăng nồng độ thuốc trong máu và nguy cơ độc tính trên cơ (đau cơ, tiêu cơ vân).",
            "clinical_guidance": "Tránh phối hợp nếu có thể hoặc hội chẩn BS kê đơn tim mạch theo dõi triệu chứng đau/yếu cơ, nước tiểu sẫm màu.",
            "source": "DDInter (Major: Clarithromycin/Erythromycin + Atorvastatin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("clarithromycin", "atorvastatin", "Major"),
                ("erythromycin", "atorvastatin", "Major"),
            ],
        },
        {
            "rule_id": "DDI-012",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "class:vka",
            "severity": "HIGH",
            "mechanism": "Clarithromycin và erythromycin ức chế chuyển hoá qua CYP và làm giảm hệ vi khuẩn tổng hợp vitamin K ở ruột, làm tăng mạnh INR và nguy cơ xuất huyết.",
            "clinical_guidance": "Tránh kê clarithromycin/erythromycin ở BN dùng kháng vitamin K (warfarin/acenocoumarol); nếu bắt buộc, cần theo dõi INR chặt chẽ và báo BS điều trị.",
            "source": "DDInter (Major: Clarithromycin/Erythromycin + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("clarithromycin", "warfarin", "Major"),
                ("erythromycin", "warfarin", "Major"),
            ],
        },
        {
            "rule_id": "DDI-013",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "amiodarone",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng kéo dài khoảng QT và ức chế chuyển hoá CYP3A4, làm tăng nguy cơ loạn nhịp thất nặng (xoắn đỉnh).",
            "clinical_guidance": "Chống chỉ định / tránh phối hợp clarithromycin hoặc erythromycin với amiodarone; để BS lựa chọn nhóm kháng sinh không kéo dài QT.",
            "source": "DDInter (Major: Clarithromycin/Erythromycin + Amiodarone); FDA Prescribing Information (Clarithromycin)",
            "ddinter_checks": [
                ("clarithromycin", "amiodarone", "Major"),
                ("erythromycin", "amiodarone", "Major"),
            ],
        },
        {
            "rule_id": "DDI-014",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "colchicine",
            "severity": "HIGH",
            "mechanism": "Clarithromycin và erythromycin ức chế mạnh CYP3A4 và P-gp, làm giảm chuyển hoá và thải trừ colchicine, dẫn đến tích luỹ gây độc tính đa cơ quan đe doạ tính mạng.",
            "clinical_guidance": "Chống chỉ định phối hợp colchicine với chất ức chế mạnh CYP3A4/P-gp (đặc biệt ở BN suy gan/suy thận); để BS chọn kháng sinh khác.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 181 tr. 51, tr. 61 & Phần 2 STT 38 tr. 168; DDInter (Major)",
            "ddinter_checks": [
                ("clarithromycin", "colchicine", "Major"),
                ("erythromycin", "colchicine", "Major"),
            ],
        },
        {
            "rule_id": "DDI-015",
            "drug_a": "clarithromycin",
            "drug_b": "ticagrelor",
            "severity": "HIGH",
            "mechanism": "Clarithromycin ức chế mạnh CYP3A4 làm tăng nồng độ ticagrelor trong huyết thanh và tăng nguy cơ xuất huyết nghiêm trọng.",
            "clinical_guidance": "Chống chỉ định phối hợp clarithromycin với ticagrelor.",
            "source": "QĐ 5948/QĐ-BYT (2021), STT 187 tr. 52 & Phần 2 STT 22 tr. 163; DDInter (Major)",
            "ddinter_checks": [("clarithromycin", "ticagrelor", "Major")],
        },
        {
            "rule_id": "DDI-016",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "carbamazepine",
            "severity": "HIGH",
            "mechanism": "Clarithromycin và erythromycin ức chế chuyển hoá carbamazepine qua CYP3A4, làm tăng nhanh nồng độ carbamazepine huyết thanh gây ngộ độc (chóng mặt, thất điều, buồn nôn, ngủ gà).",
            "clinical_guidance": "Tránh phối hợp; để BS chọn kháng sinh khác không ức chế CYP3A4 hoặc hội chẩn chuyên khoa thần kinh theo dõi nồng độ thuốc.",
            "source": "DDInter (Major: Clarithromycin/Erythromycin + Carbamazepine) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("clarithromycin", "carbamazepine", "Major"),
                ("erythromycin", "carbamazepine", "Major"),
            ],
        },
        {
            "rule_id": "DDI-017",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "cyclosporine",
            "severity": "HIGH",
            "mechanism": "Ức chế mạnh CYP3A4 và P-gp làm tăng nồng độ cyclosporine, tăng nguy cơ độc tính thận và thần kinh.",
            "clinical_guidance": "Tránh phối hợp; nếu cần dùng kháng sinh ở BN ghép tạng/dùng cyclosporine, phải hội chẩn BS chuyên khoa và theo dõi chức năng thận, nồng độ thuốc.",
            "source": "DDInter (Major: Clarithromycin/Erythromycin + Cyclosporine) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("clarithromycin", "cyclosporine", "Major"),
                ("erythromycin", "cyclosporine", "Major"),
            ],
        },
        {
            "rule_id": "DDI-018",
            "drug_a": "clarithromycin",
            "drug_b": "digoxin",
            "severity": "HIGH",
            "mechanism": "Clarithromycin ức chế P-gp tại ruột/thận và thay đổi hệ vi khuẩn ruột chuyển hoá digoxin, làm tăng nồng độ digoxin huyết thanh gây ngộ độc (loạn nhịp, buồn nôn, rối loạn thị giác).",
            "clinical_guidance": "Tránh phối hợp ở BN đang dùng digoxin; nếu bắt buộc cần hội chẩn BS tim mạch theo dõi lâm sàng và nồng độ digoxin.",
            "source": "DDInter (Major: Clarithromycin + Digoxin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("clarithromycin", "digoxin", "Major")],
        },
        # --- HIGH: Khác (Azithromycin+Amiodarone, Epinephrine+Propranolol, Methotrexate, Dexamethasone) ---
        {
            "rule_id": "DDI-019",
            "drug_a": "azithromycin",
            "drug_b": "amiodarone",
            "severity": "HIGH",
            "mechanism": "Hiệp đồng kéo dài khoảng QT trên điện tâm đồ, làm tăng nguy cơ loạn nhịp thất nghiêm trọng (xoắn đỉnh).",
            "clinical_guidance": "Tránh / chống chỉ định phối hợp với thuốc kéo dài khoảng QT như amiodarone; để BS lựa chọn phác đồ kháng sinh khác an toàn hơn.",
            "source": "FDA Drug Safety Communication / Azithromycin Label (QT prolongation); CredibleMeds (Known Risk of TdP); Drugs.com (Major)",
            "ddinter_checks": [],
        },
        {
            "rule_id": "DDI-020",
            "drug_a": "epinephrine",
            "drug_b": "propranolol",
            "severity": "HIGH",
            "mechanism": "Thuốc chẹn beta không chọn lọc (propranolol) chẹn thụ thể beta-2 giãn mạch khiến tác dụng co mạch alpha của epinephrine không bị đối kháng, có thể gây tăng huyết áp kịch phát và nhịp chậm phản xạ nguy hiểm.",
            "clinical_guidance": "Thận trọng tối đa khi dùng thuốc tê chứa epinephrine/adrenaline ở BN đang uống propranolol; đo huyết áp/mạch trước tiêm, hút ngược kỹ, hạn chế tối đa thuốc co mạch hoặc hội chẩn BS tim mạch.",
            "source": "DDInter (Major: Epinephrine + Propranolol) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("epinephrine", "propranolol", "Major")],
        },
        {
            "rule_id": "DDI-021",
            "drug_a": "amoxicillin",
            "drug_b": "methotrexate",
            "severity": "HIGH",
            "mechanism": "Penicillin (amoxicillin) cạnh tranh bài tiết qua ống thận với methotrexate, làm giảm thải trừ và tăng nguy cơ độc tính nặng của methotrexate (suy tuỷ, viêm niêm mạc, độc gan/thận).",
            "clinical_guidance": "Thận trọng tối đa / tránh phối hợp nếu có thể (đặc biệt khi BN dùng methotrexate liều trung bình–cao); hội chẩn BS chuyên khoa theo dõi công thức máu và chức năng thận.",
            "source": "DDInter (Major: Amoxicillin + Methotrexate) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("amoxicillin", "methotrexate", "Major")],
        },
        {
            "rule_id": "DDI-022",
            "drug_a": "class:nsaid",
            "drug_b": "methotrexate",
            "severity": "HIGH",
            "mechanism": "NSAID làm giảm tưới máu thận và cạnh tranh thải trừ qua ống thận với methotrexate, gây tích luỹ và độc tính nặng (suy tuỷ, xuất huyết, tổn thương gan/thận).",
            "clinical_guidance": "Tránh phối hợp NSAID với methotrexate; để BS cân nhắc giảm đau khác hoặc hội chẩn BS điều trị methotrexate.",
            "source": "DDInter (Major: Methotrexate + Ibuprofen/Naproxen/Meloxicam/Diclofenac/Ketorolac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("ibuprofen", "methotrexate", "Major"),
                ("diclofenac", "methotrexate", "Major"),
                ("meloxicam", "methotrexate", "Major"),
                ("naproxen", "methotrexate", "Major"),
                ("ketorolac", "methotrexate", "Major"),
            ],
        },
        {
            "rule_id": "DDI-023",
            "drug_a": "dexamethasone",
            "drug_b": "amiodarone",
            "severity": "HIGH",
            "mechanism": "Corticosteroid toàn thân (dexamethasone) có thể gây hạ kali máu và hiệp đồng tăng nguy cơ loạn nhịp thất (xoắn đỉnh) khi dùng chung với amiodarone.",
            "clinical_guidance": "Tránh dùng phối hợp dexamethasone toàn thân không cần thiết ở BN đang uống amiodarone; nếu cần, phải kiểm tra điện giải đồ và hội chẩn BS tim mạch.",
            "source": "DDInter (Major: Amiodarone + Dexamethasone) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("amiodarone", "dexamethasone", "Major")],
        },
        # --- MODERATE: Cần theo dõi / thận trọng rõ ràng ---
        {
            "rule_id": "DDI-024",
            "drug_a": "class:nsaid",
            "drug_b": "clopidogrel",
            "severity": "MODERATE",
            "mechanism": "Phối hợp NSAID với thuốc kháng kết tập tiểu cầu P2Y12 (clopidogrel) làm tăng nguy cơ kích ứng và xuất huyết tiêu hoá.",
            "clinical_guidance": "Hạn chế dùng NSAID kéo dài ở BN đang uống clopidogrel; cân nhắc hướng giảm đau ít ảnh hưởng tiêu hoá/tiểu cầu hơn và theo dõi dấu hiệu chảy máu.",
            "source": "DDInter (Moderate: Clopidogrel + Ibuprofen/Naproxen/Meloxicam/Diclofenac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("clopidogrel", "ibuprofen", "Moderate"),
                ("clopidogrel", "diclofenac", "Moderate"),
                ("clopidogrel", "meloxicam", "Moderate"),
                ("clopidogrel", "naproxen", "Moderate"),
            ],
        },
        {
            "rule_id": "DDI-025",
            "drug_a": "class:nsaid",
            "drug_b": "enalapril",
            "severity": "MODERATE",
            "mechanism": "NSAID làm co tiểu động mạch đến cầu thận và giữ muối nước, làm giảm hiệu quả hạ áp của thuốc ức chế men chuyển (enalapril) và tăng nguy cơ suy giảm chức năng thận.",
            "clinical_guidance": "Hạn chế thời gian dùng NSAID, theo dõi huyết áp và thận trọng đặc biệt nếu BN có bệnh thận mạn hoặc đang dùng thêm lợi tiểu.",
            "source": "DDInter (Moderate: Enalapril + Ibuprofen/Diclofenac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("enalapril", "ibuprofen", "Moderate"),
                ("enalapril", "diclofenac", "Moderate"),
            ],
        },
        {
            "rule_id": "DDI-026",
            "drug_a": "class:nsaid",
            "drug_b": "losartan",
            "severity": "MODERATE",
            "mechanism": "NSAID làm giảm tác dụng hạ áp của thuốc chẹn thụ thể angiotensin (losartan) và tăng nguy cơ tổn thương thận cấp (nhất là ở người cao tuổi hoặc mất nước).",
            "clinical_guidance": "Thận trọng, dùng ngắn ngày nhất có thể hoặc cân nhắc giảm đau ngoài nhóm NSAID; theo dõi huyết áp.",
            "source": "DDInter (Moderate: Losartan + Ibuprofen/Diclofenac) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [
                ("losartan", "ibuprofen", "Moderate"),
                ("losartan", "diclofenac", "Moderate"),
            ],
        },
        {
            "rule_id": "DDI-027",
            "drug_a": "amoxicillin",
            "drug_b": "class:vka",
            "severity": "MODERATE",
            "mechanism": "Kháng sinh phổ rộng (amoxicillin/clavulanate) làm thay đổi hệ vi khuẩn ruột tổng hợp vitamin K, có thể làm tăng INR ở một số BN đang dùng kháng vitamin K.",
            "clinical_guidance": "Có thể phối hợp khi có chỉ định nhiễm khuẩn RHM nhưng dặn BN theo dõi dấu hiệu chảy máu bất thường và kiểm tra INR nếu điều trị kéo dài hoặc có yếu tố nguy cơ.",
            "source": "DDInter (Moderate: Amoxicillin + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("amoxicillin", "warfarin", "Moderate")],
        },
        {
            "rule_id": "DDI-028",
            "drug_a": "azithromycin",
            "drug_b": "class:vka",
            "severity": "MODERATE",
            "mechanism": "Azithromycin có thể làm tăng tác dụng chống đông của warfarin/kháng vitamin K dù ít ức chế CYP hơn clarithromycin.",
            "clinical_guidance": "Thận trọng khi kê ở BN đang dùng kháng vitamin K; theo dõi dấu hiệu xuất huyết và cân nhắc kiểm tra INR nếu cần.",
            "source": "DDInter (Moderate: Azithromycin + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("azithromycin", "warfarin", "Moderate")],
        },
        {
            "rule_id": "DDI-029",
            "drug_a": "acetaminophen",
            "drug_b": "class:vka",
            "severity": "MODERATE",
            "mechanism": "Paracetamol (acetaminophen) khi dùng kéo dài hoặc liều cao lặp lại nhiều ngày có thể làm tăng nhẹ–vừa chỉ số INR ở BN đang dùng kháng vitamin K.",
            "clinical_guidance": "Vẫn thường là lựa chọn giảm đau ít nguy cơ xuất huyết tiêu hoá hơn NSAID, nhưng cần dùng ngắn ngày nhất có thể và nhắc BN theo dõi INR/dấu hiệu chảy máu nếu dùng nhiều ngày liên tiếp.",
            "source": "DDInter (Moderate: Acetaminophen + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("acetaminophen", "warfarin", "Moderate")],
        },
        {
            "rule_id": "DDI-030",
            "drug_a": "dexamethasone",
            "drug_b": "class:vka",
            "severity": "MODERATE",
            "mechanism": "Corticosteroid toàn thân có thể làm thay đổi đáp ứng chống đông (thường tăng INR) và tăng nguy cơ xuất huyết tiêu hoá khi dùng cùng kháng vitamin K.",
            "clinical_guidance": "Thận trọng nếu kê corticoid toàn thân cho BN đang uống thuốc kháng vitamin K; tránh phối hợp không thật sự cần thiết và theo dõi dấu hiệu xuất huyết.",
            "source": "DDInter (Moderate: Dexamethasone + Warfarin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("dexamethasone", "warfarin", "Moderate")],
        },
        {
            "rule_id": "DDI-031",
            "drug_a": "dexamethasone",
            "drug_b": "metformin",
            "severity": "MODERATE",
            "mechanism": "Corticosteroid (dexamethasone) làm tăng đường huyết và giảm nhạy cảm insulin, làm giảm hiệu quả kiểm soát đường huyết của metformin.",
            "clinical_guidance": "Thận trọng khi kê corticoid toàn thân cho BN đái tháo đường đang uống metformin; nhắc BN theo dõi đường huyết sát hơn trong vài ngày dùng thuốc.",
            "source": "DDInter (Moderate: Dexamethasone + Metformin) (BS RHM duyệt 27/11/2026)",
            "ddinter_checks": [("dexamethasone", "metformin", "Moderate")],
        },
        {
            "rule_id": "DDI-032",
            "drug_a": "class:macrolide_cyp3a4",
            "drug_b": "class:doac",
            "severity": "MODERATE",
            "mechanism": "Clarithromycin và erythromycin ức chế P-gp và CYP3A4 làm tăng nồng độ thuốc chống đông DOAC (rivaroxaban, apixaban, dabigatran) trong máu, tăng nguy cơ chảy máu.",
            "clinical_guidance": "Thận trọng tối đa / tránh phối hợp nếu có kháng sinh thay thế phù hợp (đặc biệt ở BN suy thận); theo dõi dấu hiệu chảy máu.",
            "source": "DDInter (Moderate: Clarithromycin/Erythromycin + Rivaroxaban/Apixaban)",
            "ddinter_checks": [
                ("clarithromycin", "rivaroxaban", "Moderate"),
                ("clarithromycin", "apixaban", "Moderate"),
                ("erythromycin", "rivaroxaban", "Moderate"),
                ("erythromycin", "apixaban", "Moderate"),
            ],
        },
        # --- MODERATE: NSAID ức chế chọn lọc COX-2 (Celecoxib) ---
        {
            "rule_id": "DDI-033",
            "drug_a": "class:nsaid_cox2",
            "drug_b": "class:vka",
            "severity": "MODERATE",
            "mechanism": "Thuốc ức chế chọn lọc COX-2 (celecoxib) có thể ức chế CYP2C9 hoặc hiệp đồng tăng nguy cơ xuất huyết tiêu hoá và tăng INR khi dùng cùng thuốc kháng vitamin K.",
            "clinical_guidance": "Thận trọng tối đa / hạn chế dùng celecoxib kéo dài ở BN đang uống kháng vitamin K (warfarin/acenocoumarol); theo dõi INR và dấu hiệu xuất huyết, để BS cân nhắc lựa chọn giảm đau ít nguy cơ hơn.",
            "source": "DDInter (Moderate: Celecoxib + Warfarin); nhóm VKA theo QĐ 5948/QĐ-BYT (2021), Phần 2 STT 43 tr. 169",
            "ddinter_checks": [("celecoxib", "warfarin", "Moderate")],
        },
        {
            "rule_id": "DDI-034",
            "drug_a": "class:nsaid_cox2",
            "drug_b": "class:doac",
            "severity": "MODERATE",
            "mechanism": "Phối hợp thuốc ức chế chọn lọc COX-2 (celecoxib) với thuốc chống đông đường uống trực tiếp (DOAC) làm tăng nguy cơ xuất huyết tiêu hoá và chảy máu.",
            "clinical_guidance": "Thận trọng / tránh dùng celecoxib kéo dài cùng DOAC; dặn BN theo dõi dấu hiệu chảy máu bất thường và để BS cân nhắc hướng giảm đau an toàn hơn.",
            "source": "DDInter (Moderate: Celecoxib + Rivaroxaban/Apixaban)",
            "ddinter_checks": [
                ("celecoxib", "rivaroxaban", "Moderate"),
                ("celecoxib", "apixaban", "Moderate"),
            ],
        },
        {
            "rule_id": "DDI-035",
            "drug_a": "class:nsaid_cox2",
            "drug_b": "class:lmwh",
            "severity": "MODERATE",
            "mechanism": "Phối hợp celecoxib với heparin trọng lượng phân tử thấp (enoxaparin) làm tăng nguy cơ chảy máu đường tiêu hoá và xuất huyết tại vết mổ.",
            "clinical_guidance": "Thận trọng khi phối hợp celecoxib với LMWH; hạn chế thời gian dùng và theo dõi dấu hiệu chảy máu.",
            "source": "DDInter (Moderate: Celecoxib + Enoxaparin)",
            "ddinter_checks": [("celecoxib", "enoxaparin", "Moderate")],
        },
        {
            "rule_id": "DDI-036",
            "drug_a": "class:nsaid_cox2",
            "drug_b": "methotrexate",
            "severity": "MODERATE",
            "mechanism": "Celecoxib có thể làm giảm tưới máu thận và giảm thải trừ methotrexate qua ống thận, làm tăng nguy cơ độc tính của methotrexate.",
            "clinical_guidance": "Thận trọng khi phối hợp celecoxib với methotrexate (đặc biệt ở người cao tuổi hoặc suy thận); để BS cân nhắc giảm đau khác hoặc theo dõi chức năng thận và công thức máu.",
            "source": "DDInter (Moderate: Celecoxib + Methotrexate)",
            "ddinter_checks": [("celecoxib", "methotrexate", "Moderate")],
        },
    ]

    for r in rules:
        for da, db, expected_lvl in r["ddinter_checks"]:
            k = tuple(sorted((da.lower(), db.lower())))
            actual = ddinter_pairs.get(k)
            if actual != expected_lvl:
                raise AssertionError(
                    f"{r['rule_id']}: DDInter kiểm cặp ({da}, {db}) ra {actual!r}, kỳ vọng {expected_lvl!r}"
                )
    return rules


def main() -> None:
    ddinter_ids, ddinter_pairs = load_ddinter()
    alias_rows = build_alias_rows(ddinter_ids)
    ddi_rows = build_ddi_rows(ddinter_pairs)

    aliases_path = DATA_DIR / "entity_aliases.csv"
    with aliases_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ALIAS_COLS)
        w.writeheader()
        w.writerows(alias_rows)

    ddi_path = DATA_DIR / "ddi_rules.csv"
    with ddi_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DDI_COLS)
        w.writeheader()
        for r in ddi_rows:
            w.writerow({col: r[col] for col in DDI_COLS})

    high_cnt = sum(1 for r in ddi_rows if r["severity"] == "HIGH")
    mod_cnt = sum(1 for r in ddi_rows if r["severity"] == "MODERATE")
    canon_cnt = len({r["canonical_id"] for r in alias_rows})
    print(f"[OK] {aliases_path.relative_to(ROOT)}: {len(alias_rows)} alias ({canon_cnt} thực thể chuẩn)")
    print(f"[OK] {ddi_path.relative_to(ROOT)}: {len(ddi_rows)} rule DDI (HIGH={high_cnt}, MODERATE={mod_cnt})")


if __name__ == "__main__":
    main()
