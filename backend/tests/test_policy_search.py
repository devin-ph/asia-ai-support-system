"""Tests for trusted keyword-based policy search."""

from __future__ import annotations

import pytest

from app.policy_search import (
    INSUFFICIENT_CONTEXT_ANSWER,
    search_policy,
)


@pytest.mark.parametrize(
    ("query", "answer_fragment", "source", "section"),
    [
        (
            "Phí vận chuyển được tính thế nào?",
            "Phí giao hàng được hiển thị",
            "docs/policies/shipping_policy.md",
            "Phí giao hàng",
        ),
        (
            "Tôi được đổi trả trong bao lâu?",
            "trong vòng 7 ngày",
            "docs/policies/return_policy.md",
            "Điều kiện và thời hạn đổi trả",
        ),
        (
            "Sản phẩm có được bảo hành không?",
            "thời hạn đã công bố",
            "docs/policies/warranty_policy.md",
            "Phạm vi và thời hạn bảo hành",
        ),
    ],
)
def test_search_policy_returns_grounded_answer_and_citation(
    query: str,
    answer_fragment: str,
    source: str,
    section: str,
) -> None:
    result = search_policy(query)

    assert answer_fragment in result.answer
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.title
    assert citation.source == source
    assert citation.section == section


def test_search_policy_returns_insufficient_context_without_match() -> None:
    result = search_policy("Có chính sách dành cho quà tặng không?")
    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.citations == ()


def test_search_policy_can_return_multiple_equally_relevant_sections() -> None:
    result = search_policy("Tôi muốn đổi trả và hỏi về hoàn tiền")
    assert "7 ngày" in result.answer
    assert "3 đến 5 ngày làm việc" in result.answer
    assert {citation.section for citation in result.citations} == {
        "Điều kiện và thời hạn đổi trả",
        "Thời gian hoàn tiền",
    }
