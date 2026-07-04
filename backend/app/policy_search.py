"""Keyword-based search over trusted Markdown policy sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.intent import normalize_vietnamese
from app.schemas import Citation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = PROJECT_ROOT / "docs" / "policies"

INSUFFICIENT_CONTEXT_ANSWER = (
    "Mình chưa có đủ thông tin trong các chính sách đáng tin cậy để trả lời "
    "chính xác câu hỏi này."
)


@dataclass(frozen=True)
class PolicyRule:
    """Allowlisted section and the keywords that may retrieve it."""

    filename: str
    section: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class PolicySearchResult:
    """Vietnamese answer plus citations to trusted sections."""

    answer: str
    citations: tuple[Citation, ...]


_RULES = (
    PolicyRule(
        filename="shipping_policy.md",
        section="Thời gian giao hàng",
        keywords=(
            "thời gian giao hàng",
            "khi nào giao",
            "bao lâu thì giao",
            "dự kiến giao",
        ),
    ),
    PolicyRule(
        filename="shipping_policy.md",
        section="Phí giao hàng",
        keywords=(
            "phí giao hàng",
            "phí vận chuyển",
            "shipping fee",
        ),
    ),
    PolicyRule(
        filename="shipping_policy.md",
        section="Theo dõi hành trình",
        keywords=(
            "theo dõi giao hàng",
            "hành trình giao hàng",
            "trạng thái giao hàng",
        ),
    ),
    PolicyRule(
        filename="return_policy.md",
        section="Điều kiện và thời hạn đổi trả",
        keywords=(
            "đổi trả",
            "đổi hàng",
            "trả hàng",
            "thời hạn đổi trả",
            "return",
        ),
    ),
    PolicyRule(
        filename="return_policy.md",
        section="Thời gian hoàn tiền",
        keywords=(
            "hoàn tiền",
            "hoàn lại",
            "thời gian hoàn tiền",
            "refund",
        ),
    ),
    PolicyRule(
        filename="warranty_policy.md",
        section="Phạm vi và thời hạn bảo hành",
        keywords=(
            "bảo hành",
            "thời hạn bảo hành",
            "phạm vi bảo hành",
            "warranty",
        ),
    ),
    PolicyRule(
        filename="warranty_policy.md",
        section="Yêu cầu tiếp nhận bảo hành",
        keywords=(
            "yêu cầu bảo hành",
            "cần gì để bảo hành",
            "tiếp nhận bảo hành",
        ),
    ),
)


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def _format_section(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current_paragraph: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            current_paragraph.append(stripped)
        elif current_paragraph:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))
    return "\n\n".join(paragraphs)


@lru_cache(maxsize=None)
def _load_policy(filename: str) -> tuple[str, dict[str, str]]:
    """Parse one trusted Markdown document into title and H2 sections."""
    path = POLICY_DIR / filename
    title = ""
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    def finish_section() -> None:
        if current_section is not None:
            sections[current_section] = _format_section(current_lines)

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            finish_section()
            current_section = line[3:].strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)
    finish_section()

    if not title:
        raise ValueError(f"Policy title missing: {path}")
    return title, sections


def search_policy(query: str) -> PolicySearchResult:
    """Return trusted policy sections matching deterministic keywords."""
    normalized_query = normalize_vietnamese(query)
    scored_rules: list[tuple[int, PolicyRule]] = []

    for rule in _RULES:
        score = 0
        for keyword in rule.keywords:
            normalized_keyword = normalize_vietnamese(keyword)
            if _contains_keyword(normalized_query, normalized_keyword):
                score += len(normalized_keyword.split())
        if score:
            scored_rules.append((score, rule))

    if not scored_rules:
        return PolicySearchResult(
            answer=INSUFFICIENT_CONTEXT_ANSWER,
            citations=(),
        )

    best_score = max(score for score, _rule in scored_rules)
    answers: list[str] = []
    citations: list[Citation] = []
    for score, rule in scored_rules:
        if score != best_score:
            continue
        title, sections = _load_policy(rule.filename)
        answer = sections.get(rule.section)
        if not answer:
            raise ValueError(
                f"Trusted policy section missing: {rule.filename}#{rule.section}"
            )
        answers.append(answer)
        citations.append(
            Citation(
                title=title,
                source=f"docs/policies/{rule.filename}",
                section=rule.section,
            )
        )

    return PolicySearchResult(
        answer="\n\n".join(answers),
        citations=tuple(citations),
    )
