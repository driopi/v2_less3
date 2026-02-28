from datetime import datetime

from app.models.checklist import ChecklistItem
from app.models.session import Answer


def build_markdown(session_id: str, topic: str, checklist: list[ChecklistItem], answers: list[Answer]) -> str:
    lines: list[str] = []
    lines.append("# Чеклист созвона с клиентом")
    lines.append("")
    lines.append(f"**Дата:** {datetime.utcnow().date().isoformat()}")
    lines.append(f"**Тема:** {topic}")
    lines.append(f"**Сессия:** {session_id}")
    lines.append("")
    lines.append("---")
    lines.append("")

    current_category = None
    for item in checklist:
        if item.category != current_category:
            current_category = item.category
            lines.append(f"## {current_category}")

        check = "x" if item.status == "confirmed" else " "
        note = f" ({item.notes})" if item.notes else ""
        lines.append(f"- [{check}] {item.item}{note}")
    lines.append("")
    lines.append("## Транскрипты")
    for answer in answers:
        lines.append(f"- Раунд {answer.round_number}: **{answer.question_text}**")
        lines.append(f"  - {answer.audio_transcript}")

    lines.append("")
    lines.append("---")
    lines.append("*Сгенерировано автоматически AI Checklist Agent*")
    return "\n".join(lines)
