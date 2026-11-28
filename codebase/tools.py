"""Công cụ tra cứu tất định trên 3 bảng CSV trong data/ — Lĩnh. Thiết kế: docs/design.md §4.4, §5.

Cả 3 công cụ đều tất định, không gọi model, KHÔNG tác động ra ngoài (chỉ đọc file CSV).

Thực thể chuẩn (entity) dùng chung giữa các công cụ là dict:
    {"canonical_id", "display_name", "entity_type", "drug_class"}
Một alias có thể có nhiều dòng trong entity_aliases.csv (thuốc phối hợp, thủ thuật nhiều nhóm),
nên bảng alias được đọc thành alias → list[dòng], không đọc vào dict theo alias (design §4.3).
"""
import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from tracing import tool, TOOLS  # noqa: F401  (TOOLS: danh sách công cụ đã đăng ký)

DATA = Path(__file__).resolve().parents[1] / "data"
LIST_KEYS = ("conditions", "allergies", "baseline_drugs", "planned_procedures", "planned_drugs")
SEVERITY_ORDER = {"HIGH": 0, "MODERATE": 1}


# ------------------------------------------------------------------ đọc dữ liệu

# Từ đệm bỏ khi so khớp, để "nhổ một răng", "nhổ cái răng" vẫn khớp alias "nho rang".
# Không alias nào chứa các từ này (đã kiểm trên entity_aliases.csv; "con" bị loại vì có "con tang huyet ap").
FILLER_WORDS = {"mot", "1", "cai", "chiec", "cac", "nhung", "vai"}
# Số răng "R36", "r11" → "r": alias "nho r" khớp mọi răng, không phải liệt kê từng số (tự thử 28/11/2026:
# "nhổ R36" không khớp alias nào nên ca warfarin mất CR-001). Mọi alias "nho r<số>" đều cùng thực thể với "nho r".
TOOTH_NUMBER = re.compile(r"^r\d{1,2}$")


def fold(text):
    """Viết thường, bỏ dấu tiếng Việt, đổi ký tự không phải chữ/số thành dấu cách, gộp khoảng trắng.
    Bộ chuẩn hoá chữ duy nhất của codebase: mọi so khớp chữ (alias, câu trả lời BS, tin xã giao) đi qua hàm này."""
    folded = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    plain = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def normalize_text(text):
    """fold() + đổi số răng thành "r" + bỏ từ đệm FILLER_WORDS — dạng dùng để so khớp alias theo ranh giới từ.
    Áp dụng giống nhau cho alias và tin nhắn."""
    words = (TOOTH_NUMBER.sub("r", w) for w in fold(text).split())
    return " ".join(w for w in words if w not in FILLER_WORDS)


def _rows(filename):
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _entity(row):
    return {"canonical_id": row["canonical_id"], "display_name": row["display_name"],
            "entity_type": row["entity_type"], "drug_class": row["drug_class"]}


@lru_cache(maxsize=1)
def _alias_index():
    """alias đã chuẩn hoá → list[thực thể]. Giữ mọi dòng của cùng một alias."""
    index = {}
    for row in _rows("entity_aliases.csv"):
        key = normalize_text(row["alias"])
        if not key:
            continue
        entities = index.setdefault(key, [])
        entity = _entity(row)
        if entity not in entities:
            entities.append(entity)
    return index


# Từ chỉ tình trạng bệnh nền (log VM 28/11). Bỏ các từ này khỏi tên bệnh để so "gốc" tên: "tăng huyết áp chưa kiểm
# soát" và "tăng huyết áp đang ổn định" cùng gốc "tang huyet ap". Dùng để biết BS đã ghi tên bệnh ĐÃ CÓ trong bảng
# kèm tình trạng, chỉ là bảng chưa có quy tắc cho tình trạng đó — khi ấy không hỏi lại Q6 (agent.py).
PROCEDURE_DRUG_CLASSES = frozenset({"local_anesthetic", "vasoconstrictor"})
STATUS_MARK = re.compile(r"\b(?:on dinh|kiem soat|dieu tri)\b")
_STATUS_WORDS = re.compile(r"\b(?:on dinh|kiem soat|dieu tri|tot|kem|dang|da|chua|khong)\b")


def condition_base(normalized_text):
    """Tên bệnh đã bỏ từ chỉ tình trạng (chuỗi đã chuẩn hoá)."""
    return " ".join(_STATUS_WORDS.sub(" ", normalized_text).split())


@lru_cache(maxsize=1)
def _condition_bases():
    return frozenset(filter(None, (condition_base(alias) for alias, ents in _alias_index().items()
                                   if any(e["entity_type"] == "condition" for e in ents))))


def known_condition_base(phrase):
    """True khi cụm bệnh nền, bỏ từ chỉ tình trạng, TRÙNG gốc tên một bệnh nền trong bảng
    (vd "cao huyết áp" là gốc của "cao huyet ap chua kiem soat"). Tên lạ ("th áp", "đặt stent") → False."""
    return condition_base(normalize_text(phrase)) in _condition_bases()


def known_condition_with_status(phrase):
    """known_condition_base và có từ chỉ tình trạng (vd "THA ổn định"). Thiếu tình trạng ("tăng huyết áp") → False."""
    return bool(STATUS_MARK.search(normalize_text(phrase))) and known_condition_base(phrase)


def find_aliases(normalized_text):
    """Tìm mọi alias trong chuỗi đã chuẩn hoá: ưu tiên khớp dài nhất, không chồng lấn (design §5 bước 2.4).
    Trả list[(alias, list[thực thể])] theo thứ tự xuất hiện."""
    candidates = []
    index = _alias_index()
    for alias in index:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", normalized_text):
            candidates.append((m.start(), m.end(), alias))
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    taken, chosen = [], []
    for start, end, alias in candidates:
        if any(start < t_end and t_start < end for t_start, t_end in taken):
            continue
        taken.append((start, end))
        chosen.append((start, alias))
    chosen.sort()
    return [(alias, index[alias]) for _, alias in chosen]


# ------------------------------------------------------------------ bước 2: chuẩn hoá

def _add(bucket, entity):
    if entity not in bucket:
        bucket.append(entity)


def _keys(entity):
    """Các khoá một thực thể khớp được trong bảng rule: canonical_id hoặc class:<drug_class>."""
    return {entity["canonical_id"], "class:" + entity["drug_class"]}


@tool
def normalize_entities(extracted, raw_text):
    """Chuẩn hoá thực thể (design §5 bước 2).
    Input: JSON model lần 1 (dict 5 danh sách, hoặc None nếu model lỗi / JSON hỏng) + tin nhắn gốc (str).
    Output: dict conditions, allergies, baseline_drugs, planned_drugs, procedure_groups, unknown_role_drugs,
            procedure_drugs (thuốc tê / co mạch không rõ vai; cũng có trong baseline_drugs và planned_drugs)
            (list thực thể chuẩn), unmapped (list chữ BS viết không có trong bảng).
            procedure_groups: mỗi phần tử là thực thể thủ thuật, drug_class = tên nhóm thủ thuật.
    Không tác động ra ngoài."""
    out = {k: [] for k in ("conditions", "allergies", "baseline_drugs", "planned_drugs",
                           "procedure_groups", "unknown_role_drugs", "procedure_drugs")}
    out["unmapped"] = []
    by_type = {"condition": "conditions", "allergy": "allergies", "procedure": "procedure_groups"}
    role_of_list = {"baseline_drugs": "baseline_drugs", "planned_drugs": "planned_drugs"}

    # 2.1–2.2: tra từng chuỗi model trả về; tìm alias nằm trong chuỗi.
    extracted = extracted or {}
    for list_name in LIST_KEYS:
        for phrase in extracted.get(list_name) or []:
            norm = normalize_text(phrase)
            found = [e for _, ents in find_aliases(norm) for e in ents]
            if list_name == "allergies":
                # Model thường chỉ ghi chất gây dị ứng ("penicillin"); alias dị ứng có dạng "di ung …".
                allergy = [e for e in found if e["entity_type"] == "allergy"]
                if not allergy:
                    allergy = [e for _, ents in find_aliases("di ung " + norm) for e in ents
                               if e["entity_type"] == "allergy"]
                found = allergy
            if not found:
                if phrase.strip() and phrase.strip() not in out["unmapped"]:
                    out["unmapped"].append(phrase.strip())
                continue
            for entity in found:
                if entity["entity_type"] == "drug":
                    role = role_of_list.get(list_name)
                    if role:
                        _add(out[role], entity)
                    else:  # model xếp thuốc vào nhóm khác → coi như chưa rõ vai
                        _add(out["unknown_role_drugs"], entity)
                else:
                    _add(out[by_type[entity["entity_type"]]], entity)

    # 2.3–2.5: quét tin gốc; thứ model sót thì thêm vào.
    # Quét chữ không hiểu câu phủ định ("chưa ghi có gây tê", "không dị ứng…"), nên khi model đọc được tin
    # thì chỉ bổ sung THUỐC (chỗ model sót nguy hiểm nhất); bệnh nền / dị ứng / thủ thuật tin theo model.
    # Khi model lỗi (extracted rỗng) thì bổ sung mọi loại thực thể.
    model_ok = bool(extracted)
    known_drug_ids = {e["canonical_id"] for k in ("baseline_drugs", "planned_drugs", "unknown_role_drugs")
                      for e in out[k]}
    for _, entities in find_aliases(normalize_text(raw_text)):
        for entity in entities:
            if entity["entity_type"] == "drug":
                if entity["canonical_id"] not in known_drug_ids:
                    _add(out["unknown_role_drugs"], entity)
                    known_drug_ids.add(entity["canonical_id"])
            elif not model_ok:
                _add(out[by_type[entity["entity_type"]]], entity)

    # Thuốc tê / co mạch không rõ vai (thường nằm trong cụm thủ thuật, vd "gây tê bằng lidocain") là thuốc dùng
    # trong thủ thuật, không phải thuốc BN đang dùng hay thuốc kê (log VM 28/11). Vẫn kiểm ở cả hai phía (DDI-020).
    out["procedure_drugs"] = [e for e in out["unknown_role_drugs"] if e["drug_class"] in PROCEDURE_DRUG_CLASSES]
    out["unknown_role_drugs"] = [e for e in out["unknown_role_drugs"] if e not in out["procedure_drugs"]]
    # Thuốc không rõ vai được kiểm ở cả hai phía để không sót tương tác.
    for entity in out["unknown_role_drugs"] + out["procedure_drugs"]:
        _add(out["baseline_drugs"], entity)
        _add(out["planned_drugs"], entity)
    return out


# ------------------------------------------------------------------ bước 3: tra bảng

def _merge(found, rule, a, b):
    """Gộp theo rule_id: một rule theo nhóm có thể khớp nhiều cặp (design §5 bước 3)."""
    item = found.setdefault(rule["rule_id"], {
        "rule_id": rule["rule_id"], "severity": rule["severity"], "a": [], "b": [],
        "mechanism": rule["mechanism"], "guidance": rule["clinical_guidance"], "source": rule["source"]})
    if a not in item["a"]:
        item["a"].append(a)
    if b not in item["b"]:
        item["b"].append(b)


BEHAVIOR_FLAGS = ("show_full_guidance", "asks_anticoagulant")


@lru_cache(maxsize=1)
def _behaviors():
    return {row["rule_id"]: row for row in _rows("rule_behavior.csv")}


def rule_behavior(rule_id):
    """Cách agent in / dùng một rule, theo data/rule_behavior.csv (rule không có dòng → mọi cờ False):
    show_full_guidance — 🟡 vẫn in đủ hướng xử trí (dòng gọn sẽ mất hành động);
    asks_anticoagulant — hướng xử trí đã hỏi thuốc chống đông, nên không hỏi lại Q8."""
    row = _behaviors().get(rule_id, {})
    return {flag: (row.get(flag) or "").strip().lower() == "yes" for flag in BEHAVIOR_FLAGS}


def _finish(found):
    items = [dict(v, a=", ".join(v["a"]), b=", ".join(v["b"])) for v in found.values()]
    return sorted(items, key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["rule_id"]))


@tool
def check_drug_interactions(baseline_drugs, planned_drugs):
    """Tra tương tác thuốc–thuốc trong data/ddi_rules.csv (design §5 bước 3).
    Input: list thực thể thuốc đang dùng, list thực thể thuốc định kê.
    Output: list {rule_id, severity, a, b, mechanism, guidance, source}, gộp theo rule_id, HIGH trước.
    Chỉ xét cặp có ít nhất một thuốc định kê. Không tác động ra ngoài."""
    others = list(planned_drugs) + [d for d in baseline_drugs if d not in planned_drugs]
    found = {}
    for rule in _rows("ddi_rules.csv"):
        for p in planned_drugs:
            for q in others:
                if p["canonical_id"] == q["canonical_id"]:
                    continue
                if rule["drug_a"] in _keys(p) and rule["drug_b"] in _keys(q):
                    _merge(found, rule, p["display_name"], q["display_name"])
                elif rule["drug_b"] in _keys(p) and rule["drug_a"] in _keys(q):
                    _merge(found, rule, q["display_name"], p["display_name"])
    return _finish(found)


@tool
def check_clinical_risks(conditions, allergies, baseline_drugs, planned_drugs, procedure_groups):
    """Tra rủi ro bệnh nền / dị ứng / thuốc nền × thuốc định kê / nhóm thủ thuật trong
    data/clinical_risk_rules.csv (design §5 bước 3).
    Input: các list thực thể chuẩn; procedure_groups là thực thể thủ thuật (drug_class = nhóm).
    Output: list {rule_id, severity, a, b, mechanism, guidance, source}, gộp theo rule_id, HIGH trước.
    Không tác động ra ngoài."""
    left_of = {"condition": conditions, "allergy": allergies, "baseline_drug": baseline_drugs}
    found = {}
    for rule in _rows("clinical_risk_rules.csv"):
        for factor in left_of.get(rule["factor_type"], []):
            if rule["factor_id"] not in _keys(factor):
                continue
            if rule["target_type"] == "planned_drug":
                for drug in planned_drugs:
                    if rule["target_id"] in _keys(drug):
                        _merge(found, rule, factor["display_name"], drug["display_name"])
            elif rule["target_type"] == "procedure_group":
                for proc in procedure_groups:
                    if proc["drug_class"] == rule["target_id"]:
                        _merge(found, rule, factor["display_name"], proc["display_name"])
    return _finish(found)
