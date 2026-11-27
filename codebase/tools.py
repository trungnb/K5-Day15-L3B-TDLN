"""Tra cứu tất định trên CSV. Các công cụ không thực hiện tác động bên ngoài."""
import csv
import unicodedata
from collections import defaultdict
from pathlib import Path

from tracing import tool, TOOLS  # noqa: F401

DATA = Path(__file__).resolve().parents[1] / "data"


def _rows(filename):
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_text(text):
    folded = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).split())


def normalize_entities(baseline_names, planned_names):
    """Map tên đã phân vai sang toàn bộ hoạt chất. Đầu vào chưa phân vai không được suy đoán."""
    index = defaultdict(list)
    for row in _rows("entity_aliases.csv"):
        if row["entity_type"] == "drug":
            index[normalize_text(row["alias"])].append(row)

    unmatched = []
    normalized = []
    for names in (baseline_names, planned_names):
        resolved = {}
        for name in names:
            matches = index.get(normalize_text(name), [])
            if not matches:
                unmatched.append(name)
            for row in matches:
                resolved[row["canonical_id"]] = row
        normalized.append(list(resolved.values()))
    baseline, planned = normalized
    return baseline, planned, unmatched


def _drug_keys(drug):
    return {drug["canonical_id"], "class:" + drug["drug_class"]}


@tool
def check_drug_interactions(baseline_drugs, planned_drugs):
    """Rà DDI. Input: hoạt chất thuốc nền và thuốc dự kiến. Output: các rule khớp. Không tác động ngoài."""
    keys = {
        frozenset((left, right))
        for baseline in baseline_drugs
        for planned in planned_drugs
        if baseline["canonical_id"] != planned["canonical_id"]
        for left in _drug_keys(baseline)
        for right in _drug_keys(planned)
    }
    return [
        rule for rule in _rows("ddi_rules.csv")
        if frozenset((rule["drug_a"], rule["drug_b"])) in keys
    ]
