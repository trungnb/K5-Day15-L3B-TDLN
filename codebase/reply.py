"""Bản tin trả lời có cấu trúc (bước 5 · design §7) và ba cách in nó.

agent.answer() dựng một Reply; mọi nơi cần chữ đều in từ Reply, không ai phải đọc ngược chuỗi đã ráp:
    render_text(reply)    → `output` cho eval / trace (nguyên văn design §7)
    render_chat(reply)    → tin đầu gửi BS trên Zalo: 🔴 🟡 gọn (nguồn để ở "chi tiết"), "đã đối chiếu" dạng gạch đầu dòng,
                            câu dẫn khi hỏi lại / từ chối (issue #31; Trung duyệt 28/11)
    render_detail(reply)  → lệnh "chi tiết": chỉ các khối cảnh báo, nguyên văn bảng tra kèm lý do và nguồn
"""
from __future__ import annotations

from dataclasses import dataclass, field

from texts import TEXT

CHECKED_PREFIX = "Đã đối chiếu — "

# Câu chữ chỉ có trên Zalo (lớp chat), gom cùng chỗ với cách in.
CHECKED_HEADER = "📋 Em đã đối chiếu:"
ASK_LEAD = "Dạ, em chưa đọc ra đủ thông tin để rà ca này."
ASK_MOI_HINT = "Hoặc nhắn /moi để bắt đầu ca khác."
REFUSAL_LEAD = "Dạ, phần này nằm ngoài việc em hỗ trợ:"
DETAIL_HINT = "(Nhắn \"chi tiết\" trong 10 phút để xem lý do, hướng xử trí 🟡 và nguồn.)"


@dataclass(frozen=True)
class Alert:
    """Một rule đã khớp, ở mọi dạng cần in."""
    rule_id: str
    severity: str               # "HIGH" | "MODERATE"
    text: str                   # dòng cảnh báo không kèm nguồn (model 2 đã kiểm, khung §7, hoặc dòng 🟡 gọn)
    source: str
    detail: str                 # dòng bản "chi tiết": nguyên văn bảng tra + lý do + nguồn
    compact_head: str = ""      # chỉ dòng 🟡 gọn: "[mã] a + b" — tin đầu trên Zalo chỉ in phần này

    @property
    def line(self) -> str:
        return f"{self.text}. Nguồn: {self.source}."

    @property
    def chat_line(self) -> str:
        return self.compact_head or f"{self.text}."


@dataclass
class Reply:
    """Các khối của bản tin theo thứ tự in (design §7). Khối rỗng không in."""
    head: list[str] = field(default_factory=list)        # 🚫 cấp cứu, ⚠️ định danh, câu báo đọc JSON lỗi
    verdict: str = ""                                     # kết luận đếm bằng code
    ok: str = ""                                          # ✅ khi không có gì cần báo
    alerts: list[Alert] = field(default_factory=list)
    together: bool = False                                # tình huống 3: tiêu đề "nếu dùng cùng nhau"
    notes: list[str] = field(default_factory=list)        # ❔ / ℹ️ / câu cố định khác
    refusals: list[str] = field(default_factory=list)     # 🚫 ngoài phạm vi (không gồm cấp cứu)
    checked: list[tuple[str, str]] = field(default_factory=list)   # mục "Đã đối chiếu": (nhãn, giá trị)
    question: str = ""                                    # câu hỏi lại / câu nhắc cuối (tối đa một)
    question_key: str = ""                                # khoá TEXT của câu đó ("Q1", "Q8", …)
    footer: bool = True
    needs_more: bool = False                              # bot giữ ca chờ ghép tin bổ sung (design §9)

    @classmethod
    def text_only(cls, text: str, needs_more: bool = False) -> "Reply":
        """Bản tin chỉ một câu cố định, không câu chốt (tin xã giao)."""
        return cls(notes=[text], footer=False, needs_more=needs_more)

    @property
    def head_only(self) -> bool:
        """Chỉ có dòng đầu tin (vd riêng dòng cấp cứu khi không nhận ra gì để đối chiếu, agent._reply)."""
        return bool(self.head) and not (self.verdict or self.ok or self.alerts or self.notes or self.refusals
                                        or self.checked or self.question)

    @property
    def is_no_entity(self) -> bool:
        """Tình huống 1/2 (§6): không nhận ra thực thể nào, chỉ hỏi lại Q1. Bot đổi lần thứ 2 liên tiếp sang REPAIR."""
        return (self.question_key == "Q1" and not self.checked and not self.alerts
                and not any("❔" in note for note in self.notes))


def _checked_text(checked: list[tuple[str, str]]) -> str:
    return CHECKED_PREFIX + " · ".join(f"{label}: {value}" for label, value in checked) if checked else ""


def _alert_blocks(reply: Reply, line_of) -> list[str]:
    suffix = "_IF_TOGETHER" if reply.together else ""
    blocks = []
    for severity in ("HIGH", "MODERATE"):
        lines = [line_of(a) for a in reply.alerts if a.severity == severity]
        if lines:
            blocks.append(TEXT[severity + "_HEADER" + suffix] + "\n" + "\n".join("- " + line for line in lines))
    return blocks


def _join(blocks: list[str]) -> str:
    return "\n".join(b for b in blocks if b)


def render_text(reply: Reply) -> str:
    """`output` của answer(): nguyên văn design §7 — eval chấm bản này."""
    return _join(reply.head + [reply.verdict, reply.ok] + _alert_blocks(reply, lambda a: a.line) + reply.notes
                 + reply.refusals + [_checked_text(reply.checked), reply.question]
                 + [TEXT["FOOTER"] if reply.footer else ""])


def _chat_checked(checked: list[tuple[str, str]]) -> list[str]:
    shown = [f"• {label}: {value}" for label, value in checked if value != TEXT["NOT_DECLARED"]]
    undeclared = [label[:1].lower() + label[1:] for label, value in checked if value == TEXT["NOT_DECLARED"]]
    if undeclared:
        shown.append("• Chưa khai: " + ", ".join(undeclared))
    return [CHECKED_HEADER] + shown


def _chat_body(reply: Reply, alert_blocks: list[str], question: str) -> list[str]:
    refusals = [REFUSAL_LEAD] + reply.refusals if reply.refusals else []
    if question == TEXT["Q1"] and not reply.checked and not reply.refusals:
        question = "\n".join((ASK_LEAD, question, ASK_MOI_HINT))
    checked = "\n".join(_chat_checked(reply.checked)) if reply.checked else ""
    return (reply.head + [reply.verdict, reply.ok] + alert_blocks + reply.notes + refusals
            + [checked, question] + [TEXT["FOOTER"] if reply.footer else ""])


def render_chat(reply: Reply, repeat_miss: bool = False) -> str:
    """Tin đầu trên Zalo. repeat_miss=True: lần thứ 2 liên tiếp không nhận ra thực thể → câu mẫu REPAIR thay Q1."""
    question = TEXT["REPAIR"] if repeat_miss and reply.is_no_entity else reply.question
    blocks = _chat_body(reply, _alert_blocks(reply, lambda a: a.chat_line), question)
    return _join(blocks + [DETAIL_HINT if reply.alerts else ""])


def render_detail(reply: Reply) -> str:
    """Lệnh "chi tiết": chỉ các khối 🔴 / 🟡 bản đủ + câu chốt — BS đã đọc kết luận và 📋 ở tin trước.
    Không có cảnh báo thì gửi lại cả bản tin (dạng chat, không câu mời "chi tiết")."""
    if not reply.alerts:
        return _join(_chat_body(reply, [], reply.question))
    return _join(_alert_blocks(reply, lambda a: a.detail) + [TEXT["FOOTER"]])
