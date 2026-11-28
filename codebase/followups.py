"""Giao thức ghép tin bổ sung giữa bot và agent (design §9) — định nghĩa ở MỘT chỗ.

Bot ghép tin BS nhắn thêm vào ca đang chờ bằng merge(); agent đọc lại các câu trả lời đó bằng replies() để biết
câu hỏi nào BS đã trả lời. answer(text) vẫn không có bộ nhớ: mọi trạng thái nằm trong chữ đã ghép.
"""
from tools import fold

LABEL = "Bổ sung"


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
