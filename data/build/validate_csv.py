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


COMBO_RE = re.compile(r"combo:([a-z0-9_]+(?:\+[a-z0-9_]+)+)")


def _combo_components(notes: str) -> list[str]:
    m = COMBO_RE.search(notes or "")
    return m.group(1).split("+") if m else []


def _check_alias_groups(
    groups: dict[str, list[tuple[int, str, str, str, list[str]]]],
    known_ids: set[str],
    errors: list[str],
    notes: list[str],
) -> int:
    """Kiểm thuốc phối hợp và thủ thuật có thêm nhóm gây tê.

    - Một alias thủ thuật có thể giữ cùng canonical_id ở hai nhóm: invasive_bleeding hoặc non_invasive, cộng local_anesthesia.
    - Alias khác chỉ được có nhiều dòng khi khai nhất quán các thành phần combo.
    - Khai combo: mỗi dòng phải là một thành phần của combo; thành phần nào đã có thực thể trong bảng
      thì phải có dòng cho alias đó (nếu không → lỗi, vì sẽ sót cảnh báo); thành phần chưa có thực thể
      → chỉ ghi chú.
    Trả về số alias phối hợp.
    """
    combo_count = 0
    for alias, rows in groups.items():
        ids = [cid for _, cid, _, _, _ in rows]
        lines = ", ".join(str(i) for i, _, _, _, _ in rows)
        types = {kind for _, _, kind, _, _ in rows}
        classes = {cls for _, _, _, cls, _ in rows}
        combos = {tuple(c) for _, _, _, _, c in rows}
        if "procedure" in types and len(rows) > 1:
            if not (
                len(rows) == 2 and len(set(ids)) == 1 and types == {"procedure"}
                and classes in ({"invasive_bleeding", "local_anesthesia"}, {"non_invasive", "local_anesthesia"})
                and combos == {()}
            ):
                errors.append(f"entity_aliases.csv dòng {lines}: alias thủ thuật {alias!r} có nhóm trùng hoặc mơ hồ")
            continue
        dup = {cid for cid in ids if ids.count(cid) > 1}
        if dup:
            errors.append(f"entity_aliases.csv dòng {lines}: alias {alias!r} trùng y hệt với {sorted(dup)!r}")
        declared = next(iter(combos)) if len(combos) == 1 else None
        if not declared:
            if len(set(ids)) > 1:
                errors.append(
                    f"entity_aliases.csv dòng {lines}: alias {alias!r} bị trùng mơ hồ giữa {sorted(set(ids))!r}"
                    + (" (các dòng khai combo khác nhau)" if len(combos) > 1 else " — nếu là thuốc phối hợp, ghi 'combo:a+b' vào notes mọi dòng")
                )
            continue
        combo_count += 1
        stray = sorted(set(ids) - set(declared))
        if stray:
            errors.append(f"entity_aliases.csv dòng {lines}: alias {alias!r} có {stray!r} không nằm trong combo:{'+'.join(declared)}")
        missing = [c for c in declared if c in known_ids and c not in ids]
        if missing:
            errors.append(
                f"entity_aliases.csv dòng {lines}: alias {alias!r} khai combo:{'+'.join(declared)} "
                f"nhưng thiếu dòng cho {missing!r} (sẽ sót cảnh báo của hoạt chất này)"
            )
        unknown = [c for c in declared if c not in known_ids]
        if unknown:
            notes.append(f"alias {alias!r}: thành phần {unknown!r} chưa có thực thể trong bảng (chưa tra được)")
    return combo_count


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
        # alias -> [(số dòng, canonical_id, loại thực thể, nhóm, thành phần combo)]
        alias_groups: dict[str, list[tuple[int, str, str, str, list[str]]]] = {}
        for idx, row in enumerate(alias_rows, start=2):
            label = f"entity_aliases.csv:{idx}"
            if not row["alias"] or not row["canonical_id"] or not row["source"]:
                errors.append(f"{label}: thiếu alias, canonical_id hoặc source")
            if row["entity_type"] not in VALID_ENTITY_TYPES:
                errors.append(f"{label}: entity_type không hợp lệ {row['entity_type']!r}")
            if row["entity_type"] == "procedure" and row["drug_class"] not in VALID_PROCEDURE_CLASSES:
                errors.append(f"{label}: thủ thuật thiếu/sai drug_class {row['drug_class']!r}")
            alias_groups.setdefault(_norm_text(row["alias"]), []).append(
                (idx, row["canonical_id"], row["entity_type"], row["drug_class"], _combo_components(row["notes"]))
            )
            if row["canonical_id"]:
                known_ids.add(row["canonical_id"])
            if row["drug_class"]:
                known_classes.add(f"class:{row['drug_class']}")
                known_classes.add(row["drug_class"])
        combo_count = _check_alias_groups(alias_groups, known_ids, errors, notes)
        notes.append(f"entity_aliases.csv: {len(alias_rows)} dòng ({combo_count} biệt dược phối hợp)")
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
