"""Bản CP2: tra DDI tất định khi người dùng nêu rõ hai nhóm thuốc."""
import re

from tools import check_drug_interactions, normalize_entities, normalize_text

BASELINE = re.compile(r"(?:thuoc nen\s*:|thuoc dang dung\s*:|(?:dang|hien) (?:dung|uong)\s+)")
PLANNED = re.compile(r"(?:thuoc dinh ke\s*:|(?:(?:toi|minh|bs)\s+)?(?:du dinh|du|dinh|sap) ke\s+)")
OUT_OF_SCOPE = re.compile(r"\b(?:tu ngung|tu nghi|bao .*? ngung|so ngay dung|lieu .*? cung|doi sang thuoc)\b")
TRAILING_REQUEST = re.compile(r"(?:nho |xin )?(?:kiem tra|ra|doi chieu) tuong tac(?: thuoc)?(?: giup minh| giup toi)?")
DELIMITER = re.compile(r"\s*(?:\+|\bva\b|,)\s*")
MISSING = "BS cho biết tên thuốc đang dùng và tên thuốc định kê để tra cặp tương tác được không?"
FOOTER = "BS là người quyết định."


def _drug_names(field, allow_request=False):
    clauses = [clause.strip(" ,") for clause in re.split(r"[.!?;]", field) if clause.strip(" ,")]
    if not clauses or len(clauses) > 2:
        return []
    if len(clauses) == 2 and not (allow_request and TRAILING_REQUEST.fullmatch(clauses[1])):
        return []
    return [item.strip() for item in DELIMITER.split(clauses[0]) if item.strip()]


def answer(text):
    normalized = normalize_text(text)
    if OUT_OF_SCOPE.search(normalized):
        return {"output": "Ngoài phạm vi: công cụ không cung cấp liều, thời gian dùng, thuốc thay thế hoặc chỉ dẫn tự ngưng thuốc nền.\n" + FOOTER}

    if re.search(r"\bchua (?:ghi|co|biet) ten\b", normalized):
        return {"output": MISSING + "\n" + FOOTER, "needs_more": True}

    baseline_markers = list(BASELINE.finditer(normalized))
    planned_markers = list(PLANNED.finditer(normalized))
    if len(baseline_markers) != 1 or len(planned_markers) != 1:
        return {"output": MISSING + "\n" + FOOTER, "needs_more": True}
    baseline_marker = baseline_markers[0]
    planned_marker = planned_markers[0]
    if baseline_marker.end() >= planned_marker.start():
        return {"output": MISSING + "\n" + FOOTER, "needs_more": True}

    before_planned = normalized[baseline_marker.end():planned_marker.start()]
    baseline_names = _drug_names(before_planned)
    planned_names = _drug_names(normalized[planned_marker.end():], allow_request=True)
    if not baseline_names or not planned_names:
        return {"output": MISSING + "\n" + FOOTER, "needs_more": True}

    baseline, planned, unmatched = normalize_entities(baseline_names, planned_names)
    lines = []
    if baseline and planned:
        checked = list(dict.fromkeys(row["display_name"] for row in baseline + planned))
        lines.append("Đã tra DDI: " + ", ".join(checked) + ".")
        rules = check_drug_interactions(baseline, planned)
        for rule in rules:
            lines.append(f"[{rule['rule_id']}] {rule['severity']} — {rule['mechanism']} Nguồn: {rule['source']}.")
        if not rules and not unmatched:
            lines.append("Chưa thấy quy tắc khớp trong bảng DDI hiện có.")
    if unmatched:
        lines.append("Chưa có dữ liệu cho một hoặc nhiều tên thuốc chưa xác định. BS kiểm tra tên hoạt chất trên nhãn hoặc Dược thư.")
    lines.append("Phạm vi bản thử: tra DDI; các nhánh bệnh nền, dị ứng và thủ thuật chưa được kiểm.")
    lines.append(FOOTER)
    return {"output": "\n".join(lines), "needs_more": bool(unmatched)}
