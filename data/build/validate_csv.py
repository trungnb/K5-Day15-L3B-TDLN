"""Kiểm tra toàn vẹn schema, khoá ngoại, trùng lặp và an toàn nội dung cho các file CSV trong data/.

Chỉ dùng thư viện chuẩn Python. Chạy từ thư mục gốc repo:
    python3 data/build/validate_csv.py
"""
from __future__ import annotations

import csv
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

ALIAS_COLS = ["alias", "canonical_id", "display_name", "entity_type", "drug_class", "notes", "source"]
DDI_COLS = ["rule_id", "drug_a", "drug_b", "severity", "mechanism", "clinical_guidance", "source"]
CR_COLS = [
    "rule_id",
    "factor_type",
    "factor_id",
    "target_type",
    "target_id",
    "severity",
    "mechanism",
    "clinical_guidance",
    "source",
]

VALID_ENTITY_TYPES = {"drug", "condition", "allergy", "procedure"}
VALID_PROCEDURE_CLASSES = {"invasive_bleeding", "local_anesthesia", "non_invasive"}
VALID_FACTOR_TYPES = {"condition", "allergy", "baseline_drug"}
VALID_TARGET_TYPES = {"planned_drug", "procedure_group"}
VALID_SEVERITIES = {"HIGH", "MODERATE"}

# Kiểm an toàn: không chứa chỉ định liều cụ thể hoặc khuyên tự ngưng thuốc nền.
DOSAGE_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|ug|g/ngày|viên/ngày|ml)\b", re.IGNORECASE)
UNSAFE_STOP_RE = re.compile(r"(?<!không\s)(?<!không tự ý\s)(?<!đừng\s)\btự ngưng\b", re.IGNORECASE)


def _norm_text(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    return " ".join(s.split())


def _read_csv(path: Path, expected_cols: list[str], errors: list[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != expected_cols:
            errors.append(
                f"{path.name}: sai header {reader.fieldnames!r} (chuẩn phải là {expected_cols!r})"
            )
            return []
        rows: list[dict[str, str]] = []
        for idx, row in enumerate(reader, start=2):
            if None in row:
                errors.append(f"{path.name}:{idx}: thừa cột so với header")
                continue
            rows.append({k: (v or "").strip() for k, v in row.items()})
        return rows


def _check_safety_text(label: str, text: str, errors: list[str]) -> None:
    if DOSAGE_RE.search(text):
        errors.append(f"{label}: chứa liều lượng cụ thể (vi phạm quy tắc không tư vấn liều)")
    if UNSAFE_STOP_RE.search(text):
        errors.append(f"{label}: chứa cụm 'tự ngưng' không kèm phủ định an toàn")


def validate_all() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []

    alias_path = DATA_DIR / "entity_aliases.csv"
    ddi_path = DATA_DIR / "ddi_rules.csv"
    cr_path = DATA_DIR / "clinical_risk_rules.csv"

    known_ids: set[str] = set()
    known_classes: set[str] = set(VALID_PROCEDURE_CLASSES)

    if alias_path.exists():
        alias_rows = _read_csv(alias_path, ALIAS_COLS, errors)
        alias_map: dict[str, str] = {}
        for idx, row in enumerate(alias_rows, start=2):
            label = f"entity_aliases.csv:{idx}"
            if not row["alias"] or not row["canonical_id"] or not row["source"]:
                errors.append(f"{label}: thiếu alias, canonical_id hoặc source")
            if row["entity_type"] not in VALID_ENTITY_TYPES:
                errors.append(f"{label}: entity_type không hợp lệ {row['entity_type']!r}")
            if row["entity_type"] == "procedure" and row["drug_class"] not in VALID_PROCEDURE_CLASSES:
                errors.append(f"{label}: thủ thuật thiếu/sai drug_class {row['drug_class']!r}")
            norm_a = _norm_text(row["alias"])
            if norm_a in alias_map and alias_map[norm_a] != row["canonical_id"]:
                errors.append(
                    f"{label}: alias {row['alias']!r} bị trùng mơ hồ giữa "
                    f"{alias_map[norm_a]!r} và {row['canonical_id']!r}"
                )
            else:
                alias_map[norm_a] = row["canonical_id"]
            if row["canonical_id"]:
                known_ids.add(row["canonical_id"])
            if row["drug_class"]:
                known_classes.add(f"class:{row['drug_class']}")
                known_classes.add(row["drug_class"])
        notes.append(f"entity_aliases.csv: {len(alias_rows)} dòng")
    else:
        notes.append("entity_aliases.csv: chưa có (bỏ qua kiểm khoá ngoại liên bảng)")

    if ddi_path.exists():
        ddi_rows = _read_csv(ddi_path, DDI_COLS, errors)
        seen_ids: set[str] = set()
        seen_pairs: set[tuple[str, str]] = set()
        for idx, row in enumerate(ddi_rows, start=2):
            rid = row["rule_id"]
            label = f"ddi_rules.csv:{idx} ({rid})"
            if not re.fullmatch(r"DDI-\d{3}", rid):
                errors.append(f"{label}: rule_id phải có dạng DDI-001")
            if rid in seen_ids:
                errors.append(f"{label}: trùng rule_id")
            seen_ids.add(rid)
            if row["severity"] not in VALID_SEVERITIES:
                errors.append(f"{label}: severity không hợp lệ {row['severity']!r}")
            for req in ("drug_a", "drug_b", "mechanism", "clinical_guidance", "source"):
                if not row[req]:
                    errors.append(f"{label}: trống cột {req}")
            pair = tuple(sorted((row["drug_a"], row["drug_b"])))
            if pair in seen_pairs:
                errors.append(f"{label}: trùng cặp đảo chiều {pair!r}")
            seen_pairs.add(pair)
            _check_safety_text(label, row["clinical_guidance"], errors)
            if known_ids:
                for col in ("drug_a", "drug_b"):
                    val = row[col]
                    if val not in known_ids and val not in known_classes:
                        errors.append(f"{label}: {col}={val!r} chưa có trong entity_aliases.csv")
        notes.append(f"ddi_rules.csv: {len(ddi_rows)} dòng")
    else:
        notes.append("ddi_rules.csv: chưa có")

    if cr_path.exists():
        cr_rows = _read_csv(cr_path, CR_COLS, errors)
        seen_ids = set()
        seen_combos: set[tuple[str, str, str, str]] = set()
        for idx, row in enumerate(cr_rows, start=2):
            rid = row["rule_id"]
            label = f"clinical_risk_rules.csv:{idx} ({rid})"
            if not re.fullmatch(r"CR-\d{3}", rid):
                errors.append(f"{label}: rule_id phải có dạng CR-001")
            if rid in seen_ids:
                errors.append(f"{label}: trùng rule_id")
            seen_ids.add(rid)
            if row["factor_type"] not in VALID_FACTOR_TYPES:
                errors.append(f"{label}: factor_type không hợp lệ {row['factor_type']!r}")
            if row["target_type"] not in VALID_TARGET_TYPES:
                errors.append(f"{label}: target_type không hợp lệ {row['target_type']!r}")
            if row["severity"] not in VALID_SEVERITIES:
                errors.append(f"{label}: severity không hợp lệ {row['severity']!r}")
            for req in ("factor_id", "target_id", "mechanism", "clinical_guidance", "source"):
                if not row[req]:
                    errors.append(f"{label}: trống cột {req}")
            combo = (row["factor_type"], row["factor_id"], row["target_type"], row["target_id"])
            if combo in seen_combos:
                errors.append(f"{label}: trùng tổ hợp {combo!r}")
            seen_combos.add(combo)
            _check_safety_text(label, row["clinical_guidance"], errors)
            if known_ids:
                for col in ("factor_id", "target_id"):
                    val = row[col]
                    if val not in known_ids and val not in known_classes:
                        errors.append(f"{label}: {col}={val!r} chưa có trong entity_aliases.csv")
        notes.append(f"clinical_risk_rules.csv: {len(cr_rows)} dòng")
    else:
        errors.append("clinical_risk_rules.csv: chưa tồn tại")

    return errors, notes


def main() -> int:
    errors, notes = validate_all()
    print("=== Kiểm tra CSV trong data/ ===")
    for n in notes:
        print(f"  • {n}")
    if errors:
        print(f"\n[FAIL] Phát hiện {len(errors)} lỗi:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("\n[OK] 0 lỗi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
