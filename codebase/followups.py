"""Giao thức ghép tin bổ sung giữa bot và agent (design §9) — định nghĩa ở MỘT chỗ.

Bot ghép tin BS nhắn thêm vào ca đang chờ bằng merge(); agent đọc lại các câu trả lời đó bằng replies() để biết
câu hỏi nào BS đã trả lời. answer(text) vẫn không có bộ nhớ: mọi trạng thái nằm trong chữ đã ghép.
"""
import re

from texts import TEXT
from tools import declared_none, find_aliases, fold, normalize_text

LABEL = "Bổ sung"
# Tin tả BN (giới, tuổi) là mở đầu một ca: tin trả lời câu bot hỏi hầu như không nhắc lại (log VM 28/11 15:35).
# So trên chữ có dấu để "BN nằm viện" không thành "BN nam".
_PATIENT_INTRO = re.compile(r"\b(?:bn|bệnh nhân)\s+(?:nam|nữ)\b|\b\d{1,3}\s*tuổi\b", re.IGNORECASE)
_GROUP_OF_LABEL = {"Bệnh nền": "conditions", "Dị ứng": "allergies", "Thuốc đang dùng": "baseline_drugs",
                   "Thuốc đã nêu (chưa rõ đang dùng hay định kê)": "baseline_drugs"}


def merge(case_text: str, follow_up: str) -> str:
    """Ca đang chờ + một tin bổ sung → một tin mới cho agent."""
    return f"{case_text}\n{LABEL}: {follow_up}"


def replies(text: str) -> list[list[str]]:
    """Các tin bổ sung đã ghép trong `text`, theo thứ tự; mỗi tin là danh sách từ đã fold(), bỏ nhãn."""
    label = fold(LABEL).split()
    out = []
    for line in (text or "").split("\n"):
        words = fold(line).split()
        if words[:len(label)] == label:
            out.append(words[len(label):])
    return out


def new_patient(checked: list[tuple[str, str]], follow_up: str) -> bool:
    """Tin tới khi ca đang chờ là BN khác (không ghép): tin tả BN (giới / tuổi), hoặc BS phủ nhận cả một nhóm mà ca
    chờ đã có ("không có bệnh lý gì" khi ca chờ ghi "Bệnh nền: Đang mang thai"). `checked` là mục "Đã đối chiếu"
    của bản tin ca chờ. Phủ nhận nhóm ca chờ chưa có ("không dị ứng thuốc") là trả lời bổ sung, vẫn ghép."""
    if _PATIENT_INTRO.search(follow_up or ""):
        return True
    empty = {TEXT["NOT_DECLARED"], TEXT["NOT_RECOGNIZED"], TEXT["DECLARED_NONE"]}
    filled = {_GROUP_OF_LABEL[label] for label, value in checked if label in _GROUP_OF_LABEL and value not in empty}
    return bool(declared_none(follow_up) & filled)


# Đổi thuốc định kê qua tin bổ sung (log VM 28/11 16:24, Trung yêu cầu sửa 28/11). So trên chữ đã normalize_text().
_SWITCH = re.compile(r"\b(?:doi|chuyen) (?:sang|thanh|qua)\b|\bthay bang\b")
_DROP = re.compile(r"\b(?:bo(?! sung)|thoi(?! gian)|khong ke|ko ke|khong dung|thay vi|thay cho) (.*)")
_DROP_END = re.compile(r"\b(?:ke|cho|dung|doi|chuyen|sang|thay|ma)\b")
_ADD = re.compile(r"\b(?:them|kem|cung|ca|phoi hop|va|voi)\b")
_CLAUSE = re.compile(r"[,.;!?\n+]+")


def _segments(text: str) -> list[str]:
    """Ca gốc rồi từng tin bổ sung (mỗi tin có thể nhiều dòng), theo thứ tự."""
    label = fold(LABEL).split()
    segments = [""]
    for line in (text or "").split("\n"):
        if fold(line).split()[:len(label)] == label:
            segments.append(line.split(":", 1)[1] if ":" in line else "")
        else:
            segments[-1] += "\n" + line
    return segments


def _drug_ids(text: str, ids: set) -> set:
    return {e["canonical_id"] for _, ents in find_aliases(normalize_text(text)) for e in ents} & ids


def planned_changes(text: str, planned: list) -> tuple[set, tuple]:
    """Thuốc định kê BS đã đổi qua tin bổ sung. `planned` là thực thể thuốc định kê đã chuẩn hoá của cả ca ghép.
    Trả (canonical_id cần bỏ, (thuốc cũ, thuốc mới) nếu tin bổ sung cuối nêu thuốc mới mà không rõ thêm hay đổi).
    Tin nói rõ đổi ("đổi sang Y", "thay bằng Y") bỏ thuốc định kê của các tin trước mà tin này không nhắc lại;
    "bỏ / thôi / không kê X (nữa)", "thay vì X" bỏ X. Không rõ thì giữ cả hai: bỏ nhầm là sót cảnh báo.
    Thuốc không thấy alias trong tin nào (vd khớp gần đúng) thì không đụng tới."""
    ids = {e["canonical_id"] for e in planned}
    segments = _segments(text)
    active = _drug_ids(segments[0], ids)
    seen = set(active)
    unclear = ()
    for i, segment in enumerate(segments[1:], 1):
        clauses = [normalize_text(c) for c in _CLAUSE.split(segment)]
        removed = set()
        for clause in clauses:
            m = _DROP.search(clause)
            if m:
                removed |= _drug_ids(_DROP_END.split(m.group(1))[0], ids)
        named = _drug_ids(segment, ids) - removed
        switch = any(_SWITCH.search(c) for c in clauses)
        new, old = named - seen, (active - named - removed)
        seen |= named | removed
        active = named if switch else (active - removed) | named
        if i == len(segments) - 1 and new and old and not (switch or removed or _ADD.search(normalize_text(segment))):
            unclear = (old, new)
    return seen - active, unclear
