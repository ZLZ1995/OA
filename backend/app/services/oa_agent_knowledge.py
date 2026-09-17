"""Read-only retrieval from the versioned repository support manual."""

from functools import lru_cache
from pathlib import Path
import re

MANUAL_PATH = Path(__file__).resolve().parents[3] / "docs" / "agent-support-manual.md"
MANUAL_URL = "https://github.com/ZLZ1995/OA/blob/main/docs/agent-support-manual.md"
MAX_KNOWLEDGE_CHARS = 9000


def _terms(text: str) -> set[str]:
    terms = set(re.findall(r"[a-z0-9_]{3,}", text.lower()))
    for word in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.update(word[i:i + 2] for i in range(len(word) - 1))
    return terms - {"项目", "怎么", "如何", "请问", "可以", "什么", "当前", "系统"}


@lru_cache(maxsize=1)
def _load_sections() -> tuple[tuple[str, str], ...]:
    try:
        content = MANUAL_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ()
    sections = []
    title, lines = "", []
    for line in content.splitlines():
        if re.match(r"^#{2,3} ", line):
            if title and any(line.strip() for line in lines):
                sections.append((title, "\n".join(lines).strip()))
            title, lines = line.lstrip("# "), []
        else:
            lines.append(line)
    if title and lines:
        sections.append((title, "\n".join(lines).strip()))
    return tuple(sections)


def retrieve_manual(message: str) -> list[tuple[str, str]]:
    query = _terms(message[:4000])
    if not query:
        return []
    scored = []
    for index, (title, body) in enumerate(_load_sections()):
        matches = query & _terms(title + "\n" + body)
        if len(matches) < min(2, len(query)):
            continue
        # Normalize for section length so the broad FAQ table does not dominate every query.
        score = (len(matches) + 3 * len(query & _terms(title))) / (1 + len(body) / 1800)
        scored.append((score, index, title, body))
    scored.sort(key=lambda item: (-item[0], item[1]))
    result, remaining = [], MAX_KNOWLEDGE_CHARS
    for _, _, title, body in scored[:3]:
        budget = min(4000, remaining - len(title) - 8)
        if budget <= 0:
            break
        excerpt = body[:budget]
        if not excerpt:
            break
        result.append((title, excerpt))
        remaining -= len(title) + len(excerpt) + 8
    return result


def knowledge_context(message: str) -> str:
    sections = retrieve_manual(message)
    if not sections:
        return "未检索到相关说明书内容；不要编造操作规则。"
    return "\n\n".join(f"### {title}\n{body}" for title, body in sections)


def manual_fallback(message: str) -> str:
    sections = retrieve_manual(message)
    if not sections:
        return "请补充具体操作、报错提示；若要查询项目当前进度，请提供项目名称、项目编号或客户名称。"
    title, body = sections[0]
    # Prefer relevant, complete paragraphs/rows over cutting a large table mid-row.
    query = _terms(message)
    blocks = [block.strip() for block in body.split("\n\n") if block.strip()]
    excerpt = []
    for block in blocks:
        if block.startswith("|"):
            rows = [row for row in block.splitlines() if len(query & _terms(row)) >= min(2, len(query))]
            rows.sort(key=lambda row: -len(query & _terms(row)))
            block = "\n".join("；".join(cell.strip() for cell in row.strip("|").split("|")) for row in rows[:3])
        if len(block) > 1800:
            block = "\n".join(line for line in block.splitlines() if query & _terms(line))[:1800]
        if block and sum(map(len, excerpt)) + len(block) <= 1800:
            excerpt.append(block)
    return f"说明书指引（{title}）：\n" + "\n\n".join(excerpt) + f"\n\n参考：[OA 使用支持说明书]({MANUAL_URL})"
