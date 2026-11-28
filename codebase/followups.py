"""Giao thức ghép tin bổ sung giữa bot và agent (design §9) — định nghĩa ở MỘT chỗ.

Bot ghép tin BS nhắn thêm vào ca đang chờ bằng merge(); agent đọc lại các câu trả lời đó bằng replies() để biết
câu hỏi nào BS đã trả lời. answer(text) vẫn không có bộ nhớ: mọi trạng thái nằm trong chữ đã ghép.
"""
import re

from texts import TEXT
from tools import declared_none, fold

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
