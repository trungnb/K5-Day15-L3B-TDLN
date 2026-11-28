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
# Tên NHÓM thuốc khi chưa biết tên thuốc ("uống chống đông", "thuốc kháng tiểu cầu"; log VM 28/11 14:59) → các nhóm
# thuốc cụ thể thay thế nó: có tên thuốc cụ thể thì bỏ thực thể nhóm (CR-022 / CR-023 chỉ dành cho lúc chưa rõ tên).
# BS hay gọi chung aspirin / clopidogrel là "chống đông" (log VM 15:29: "chống đông" rồi "đang uống aspirin"), nên tên
# thuốc chống huyết khối nào cũng trả lời được câu hỏi tên, cho cả hai nhóm.
# "NSAID" (log VM 15:34: BN mang thai + "kê NSAID được không") mang drug_class nsaid để rule theo nhóm (CR-013, DDI-001…)
# chạy, nên khoá là canonical_id, không phải drug_class.
ANTITHROMBOTIC_CLASSES = frozenset({"vka", "doac", "lmwh", "antiplatelet", "p2y12_antiplatelet"})
UNSPECIFIED_DRUG_CLASSES = {"anticoagulant_unspecified": ANTITHROMBOTIC_CLASSES,
                            "antiplatelet_unspecified": ANTITHROMBOTIC_CLASSES,
                            "nsaid_unspecified": frozenset({"nsaid", "nsaid_cox2"}),
                            "cephalosporin_unspecified": frozenset({"cephalosporin"})}   # log VM 16:09
# Tên nhóm cần BS hỏi BN tên thuốc (bot giữ ca). Các tên nhóm khác là thuốc BS định kê: rule theo nhóm chạy, kèm ❔
# CLASS_ONLY (rule riêng từng thuốc cần tên).
ASK_NAME_CLASSES = frozenset({"anticoagulant_unspecified", "antiplatelet_unspecified"})
STATUS_MARK = re.compile(r"\b(?:on dinh|kiem soat|dieu tri)\b")
_STATUS_WORDS = re.compile(r"\b(?:on dinh|kiem soat|dieu tri|tot|kem|dang|da|chua|khong)\b")


# BS ghi rõ BN không có cả nhóm (PR #54; dùng cả ở followups.new_patient) → mục "Đã đối chiếu" ghi "không có" thay "không khai", không nhắc Q4 (Trung chọn 28/11).
# Chỉ khớp khi cụm phủ định đứng cuối một vế (tách theo , . ; ! ? xuống dòng), để "không bệnh tim", "không dị ứng thuốc
# tê", "không dùng thuốc chống đông" — chỉ loại một bệnh / một nhóm — không bị tính là "không có"; "và / hay / với"
# cũng tách vế. "Khoẻ mạnh" (không có "không/chưa" ngay trước) chỉ tính cho bệnh nền, không đóng Q8.
_NEG = r"(?:khong|ko|k|chua)"
_TAIL = r"(?: (?:gi|nao))?(?: (?:ca|het|nhe|a|dau))*$"
_NONE_CLAUSE = {
    "conditions": re.compile(r"(?<!khong )(?<!ko )(?<!k )(?<!chua )\bkhoe manh\b|\b%s (?:co )?(?:tien su )?(?:benh ly|benh nen|benh)%s"
                             r"|\b(?:benh nen|benh ly) %s(?: co| ghi nhan)?$" % (_NEG, _TAIL, _NEG)),
    "allergies": re.compile(r"\b%s (?:co )?(?:tien su )?di ung(?: thuoc)?%s|\bdi ung(?: thuoc)? %s(?: co)?$"
                            % (_NEG, _TAIL, _NEG)),
    "baseline_drugs": re.compile(r"\b%s (?:dung|uong|su dung|co) thuoc%s|\bthuoc (?:dang )?(?:dung|uong) %s(?: co)?$"
                                 % (_NEG, _TAIL, _NEG)),
}
_CLAUSE_SPLIT = re.compile(r"[,.;!?\n]+")
_WORD_SPLIT = re.compile(r"\b(?:va|hay|voi)\b")


def declared_none(text: str) -> frozenset:
    """Nhóm BS ghi rõ là BN không có: "conditions", "allergies", "baseline_drugs"."""
    clauses = [p.strip() for c in _CLAUSE_SPLIT.split(text or "") for p in _WORD_SPLIT.split(fold(c))]
    return frozenset(key for key, pattern in _NONE_CLAUSE.items() if any(pattern.search(c) for c in clauses))

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


# ------------------------------------------------------------------ so gần đúng (tên hơi sai chính tả)

# Log VM 28/11 14:57: "dị ứng peniciline" không khớp alias nào nên sót 🔴 CR-008. Chữ model trả mà không khớp alias
# được so gần đúng với alias CÙNG LOẠI thực thể của danh sách đó; tin trả lời ghi rõ "em hiểu … là …" (agent.py).
NEAR_MATCH_TYPES = {"allergies": "allergy", "baseline_drugs": "drug", "planned_drugs": "drug",
                    "conditions": "condition", "planned_procedures": "procedure"}
NEAR_MATCH_MIN_LEN = 5   # alias ngắn hơn ("ibu", "af", "tha") không so gần đúng: quá dễ trùng nhầm
_ALLERGY_PREFIX = "di ung "


def _edit_distance(a, b, limit):
    """Khoảng cách sửa (thêm / bớt / thay / đổi chỗ 2 ký tự liền nhau). Vượt `limit` thì trả limit + 1."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _near_limit(length):
    """Số lỗi chấp nhận theo độ dài tên (bỏ dấu cách): 5–8 ký tự → 1, từ 9 ký tự → 2."""
    return 0 if length < NEAR_MATCH_MIN_LEN else 1 if length <= 8 else 2


def near_match(normalized_phrase, list_name):
    """Alias gần đúng duy nhất cho một chữ không khớp alias nào: (alias, list[thực thể]) hoặc None.
    So từng cụm từ liên tiếp của chữ (cùng số từ với alias, ±1 để bắt tách / dính chữ), bỏ dấu cách.
    Nhiều thực thể khác nhau cùng gần nhất → không đoán (None)."""
    entity_type = NEAR_MATCH_TYPES.get(list_name)
    words = normalized_phrase.removeprefix(_ALLERGY_PREFIX).split()
    if not entity_type or not words:
        return None
    best, hits = None, {}
    for alias, entities in _alias_index().items():
        matching = [e for e in entities if e["entity_type"] == entity_type]
        target = alias.removeprefix(_ALLERGY_PREFIX).replace(" ", "")
        limit = _near_limit(len(target))
        if not matching or not limit:
            continue
        size = len(alias.removeprefix(_ALLERGY_PREFIX).split())
        for k in {max(1, size - 1), size, size + 1}:
            for start in range(len(words) - k + 1):
                d = _edit_distance("".join(words[start:start + k]), target, limit)
                if d <= limit and (best is None or d <= best):
                    if best is None or d < best:
                        best, hits = d, {}
                    hits.setdefault(frozenset(e["canonical_id"] for e in matching), (alias, matching))
    return next(iter(hits.values())) if len(hits) == 1 else None


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
    out["near_matches"] = []   # (chữ BS viết, tên trong bảng) khớp gần đúng — tin trả lời ghi "em hiểu … là …"
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
                near = near_match(norm, list_name)
                if near:
                    found = near[1]
                    out["near_matches"].append((phrase.strip(), near[1][0]["display_name"]))
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
                # Tên nhóm chỉ nhận khi model xếp vào danh sách thuốc: quét chữ không hiểu "không dùng chống đông".
                if entity["canonical_id"] in UNSPECIFIED_DRUG_CLASSES:
                    continue
                if entity["canonical_id"] not in known_drug_ids:
                    _add(out["unknown_role_drugs"], entity)
                    known_drug_ids.add(entity["canonical_id"])
            elif not model_ok:
                _add(out[by_type[entity["entity_type"]]], entity)

    # Thuốc tê / co mạch không rõ vai (thường nằm trong cụm thủ thuật, vd "gây tê bằng lidocain") là thuốc dùng
    # trong thủ thuật, không phải thuốc BN đang dùng hay thuốc kê (log VM 28/11). Vẫn kiểm ở cả hai phía (DDI-020).
    named = {e["drug_class"] for k in ("baseline_drugs", "planned_drugs", "unknown_role_drugs") for e in out[k]
             if e["canonical_id"] not in UNSPECIFIED_DRUG_CLASSES}
    for k in ("baseline_drugs", "planned_drugs", "unknown_role_drugs"):
        out[k] = [e for e in out[k] if not UNSPECIFIED_DRUG_CLASSES.get(e["canonical_id"], frozenset()) & named]
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
