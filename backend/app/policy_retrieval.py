"""Deterministic in-memory retrieval over allowlisted policy H2 sections."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.intent import normalize_vietnamese

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_POLICY_SOURCES = frozenset(
    {
        "docs/policies/return_policy.md",
        "docs/policies/shipping_policy.md",
        "docs/policies/warranty_policy.md",
    }
)

DEFAULT_TOP_K = 2
MIN_RETRIEVAL_SCORE = 0.24
MIN_MATCHED_QUERY_TOKENS = 2

LEXICAL_WEIGHT = 0.66
NGRAM_WEIGHT = 0.17
HEADING_WEIGHT = 0.10
EXACT_PHRASE_WEIGHT = 0.07

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SLUG_SEPARATOR_PATTERN = re.compile(r"[^a-z0-9]+")
_TOKEN_ALIASES = {
    "cuoc": "phi",
    "han": "gian",
}
_STOP_WORDS = frozenset(
    {
        "ai",
        "bia",
        "bi",
        "bo",
        "cach",
        "chi",
        "cho",
        "co",
        "cua",
        "cu",
        "da",
        "dan",
        "de",
        "den",
        "do",
        "duoc",
        "gi",
        "hang",
        "hay",
        "huong",
        "khi",
        "kiem",
        "khong",
        "khach",
        "la",
        "lam",
        "luc",
        "lieu",
        "luon",
        "lap",
        "may",
        "mot",
        "moi",
        "nao",
        "neu",
        "noi",
        "phai",
        "pham",
        "phot",
        "qua",
        "quen",
        "quy",
        "ra",
        "sau",
        "sach",
        "san",
        "tai",
        "that",
        "the",
        "thi",
        "thuc",
        "thong",
        "tin",
        "toi",
        "truoc",
        "tu",
        "tuc",
        "xu",
        "ly",
        "yeu",
        "cau",
        "ngay",
        "nhieu",
        "chinh",
        "dinh",
        "hua",
        "lo",
        "va",
        "vao",
        "ve",
        "voi",
    }
)


class PolicyCorpusError(ValueError):
    """Raised when an allowlisted policy cannot form a valid corpus."""


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    """One stable, citation-ready H2 evidence unit."""

    evidence_id: str
    title: str
    source: str
    section: str
    text: str


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """One ranked evidence unit with its deterministic similarity score."""

    evidence: PolicyEvidence
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Sufficient top-k evidence or an explicit refusal result."""

    evidence: tuple[PolicyEvidence, ...]
    sufficient: bool


def load_policy_corpus(
    *,
    project_root: Path = PROJECT_ROOT,
    allowed_sources: Iterable[str] = ALLOWED_POLICY_SOURCES,
) -> tuple[PolicyEvidence, ...]:
    """Load only explicit repository-relative sources in deterministic order."""
    root = project_root.resolve()
    sources = tuple(allowed_sources)
    if len(sources) != len(set(sources)):
        raise PolicyCorpusError("Policy allowlist contains duplicate sources")

    evidence: list[PolicyEvidence] = []
    for source in sorted(sources):
        path = _resolve_policy_path(root, source)
        if not path.is_file():
            raise PolicyCorpusError(f"Allowlisted policy not found: {source}")
        evidence.extend(_parse_policy(path, source))

    if not evidence:
        raise PolicyCorpusError("Policy allowlist produced no H2 evidence")
    return tuple(evidence)


class LocalPolicyRetriever:
    """Rank local H2 evidence with lightweight lexical and word-ngram scoring."""

    def __init__(
        self,
        evidence: Iterable[PolicyEvidence] | None = None,
        *,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = MIN_RETRIEVAL_SCORE,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not math.isfinite(min_score) or not 0 <= min_score <= 1:
            raise ValueError("min_score must be between 0 and 1")

        loaded = tuple(evidence) if evidence is not None else load_policy_corpus()
        if not loaded:
            raise ValueError("retriever requires at least one evidence unit")
        ordered = tuple(sorted(loaded, key=lambda item: item.evidence_id))
        evidence_ids = [item.evidence_id for item in ordered]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")

        self.evidence = ordered
        self.top_k = top_k
        self.min_score = min_score
        self._document_tokens = {
            item.evidence_id: frozenset(_tokenize(f"{item.title} {item.section} {item.text}"))
            for item in ordered
        }
        self._heading_tokens = {
            item.evidence_id: frozenset(_tokenize(item.section)) for item in ordered
        }
        self._document_bigrams = {
            item.evidence_id: _word_ngrams(_tokenize(f"{item.title} {item.section} {item.text}"), 2)
            for item in ordered
        }
        self._document_trigrams = {
            item.evidence_id: _word_ngrams(_tokenize(f"{item.title} {item.section} {item.text}"), 3)
            for item in ordered
        }
        self._document_fourgrams = {
            item.evidence_id: _word_ngrams(_tokenize(f"{item.title} {item.section} {item.text}"), 4)
            for item in ordered
        }
        self._idf = _build_idf(self._document_tokens.values())
        self._out_of_vocabulary_idf = math.log(len(ordered) + 1) + 1

    def rank(self, query: str) -> tuple[RetrievalCandidate, ...]:
        """Return all evidence sorted by score, then stable ID for ties."""
        query_tokens = tuple(_tokenize(query))
        if not query_tokens:
            return ()
        query_set = frozenset(query_tokens)
        query_weight = sum(self._token_idf(token) for token in query_set)
        query_bigrams = _word_ngrams(query_tokens, 2)
        query_trigrams = _word_ngrams(query_tokens, 3)
        query_fourgrams = _word_ngrams(query_tokens, 4)

        candidates: list[RetrievalCandidate] = []
        for item in self.evidence:
            evidence_id = item.evidence_id
            lexical_score = _weighted_overlap(
                query_set,
                self._document_tokens[evidence_id],
                query_weight,
                self._token_idf,
            )
            heading_score = _weighted_overlap(
                query_set,
                self._heading_tokens[evidence_id],
                query_weight,
                self._token_idf,
            )
            bigram_score = _set_coverage(
                query_bigrams,
                self._document_bigrams[evidence_id],
            )
            trigram_score = _set_coverage(
                query_trigrams,
                self._document_trigrams[evidence_id],
            )
            ngram_score = 0.7 * bigram_score + 0.3 * trigram_score
            exact_phrase_score = float(
                bool(query_fourgrams & self._document_fourgrams[evidence_id])
                or _heading_phrase_matches(item.section, query_tokens)
            )
            score = (
                LEXICAL_WEIGHT * lexical_score
                + NGRAM_WEIGHT * ngram_score
                + HEADING_WEIGHT * heading_score
                + EXACT_PHRASE_WEIGHT * exact_phrase_score
            )
            candidates.append(RetrievalCandidate(evidence=item, score=round(score, 6)))

        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (-candidate.score, candidate.evidence.evidence_id),
            )
        )

    def retrieve(self, query: str) -> RetrievalResult:
        """Return threshold-qualified evidence without per-query exceptions."""
        ranked = self.rank(query)
        if not ranked or ranked[0].score < self.min_score:
            return RetrievalResult(evidence=(), sufficient=False)

        query_tokens = frozenset(_tokenize(query))
        top_evidence_id = ranked[0].evidence.evidence_id
        matched_tokens = query_tokens & self._document_tokens[top_evidence_id]
        if len(matched_tokens) < MIN_MATCHED_QUERY_TOKENS:
            return RetrievalResult(evidence=(), sufficient=False)

        selected = tuple(
            candidate.evidence
            for candidate in ranked[: self.top_k]
            if candidate.score >= self.min_score
        )
        return RetrievalResult(evidence=selected, sufficient=True)

    def _token_idf(self, token: str) -> float:
        return self._idf.get(token, self._out_of_vocabulary_idf)


def _resolve_policy_path(root: Path, source: str) -> Path:
    if not source or "\\" in source:
        raise PolicyCorpusError(
            f"Policy source must use a repository-relative POSIX path: {source}"
        )
    relative = PurePosixPath(source)
    if relative.is_absolute() or ".." in relative.parts:
        raise PolicyCorpusError(f"Policy source escapes the repository root: {source}")
    path = root.joinpath(*relative.parts).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PolicyCorpusError(f"Policy source escapes the repository root: {source}") from exc
    return path


def _parse_policy(path: Path, source: str) -> tuple[PolicyEvidence, ...]:
    title = ""
    sections: list[tuple[str, list[str]]] = []
    current_section: str | None = None
    current_lines: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            if current_section is not None:
                sections.append((current_section, current_lines))
            current_section = line[3:].strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)
    if current_section is not None:
        sections.append((current_section, current_lines))

    if not title:
        raise PolicyCorpusError(f"Policy title missing: {source}")
    if not sections:
        raise PolicyCorpusError(f"Policy has no H2 sections: {source}")

    slug_counts: Counter[str] = Counter()
    evidence: list[PolicyEvidence] = []
    for section, lines in sections:
        if not section:
            raise PolicyCorpusError(f"Policy contains an empty H2 heading: {source}")
        text = _format_section(lines)
        if not text:
            raise PolicyCorpusError(f"Policy section has no text: {source}#{section}")
        base_slug = _slugify(section)
        slug_counts[base_slug] += 1
        occurrence = slug_counts[base_slug]
        slug = base_slug if occurrence == 1 else f"{base_slug}-{occurrence}"
        evidence.append(
            PolicyEvidence(
                evidence_id=f"{source}#{slug}",
                title=title,
                source=source,
                section=section,
                text=text,
            )
        )
    return tuple(evidence)


def _format_section(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def _slugify(value: str) -> str:
    normalized = normalize_vietnamese(value)
    slug = _SLUG_SEPARATOR_PATTERN.sub("-", normalized).strip("-")
    if not slug:
        raise PolicyCorpusError(f"Policy heading cannot form a stable ID: {value!r}")
    return slug


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = normalize_vietnamese(value)
    return tuple(
        _TOKEN_ALIASES.get(token, token)
        for token in _TOKEN_PATTERN.findall(normalized)
        if (len(token) > 1 or token.isdigit()) and token not in _STOP_WORDS
    )


def _word_ngrams(tokens: tuple[str, ...], size: int) -> frozenset[tuple[str, ...]]:
    if len(tokens) < size:
        return frozenset()
    return frozenset(tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1))


def _build_idf(document_tokens: Iterable[frozenset[str]]) -> dict[str, float]:
    documents = tuple(document_tokens)
    document_frequency: Counter[str] = Counter()
    for tokens in documents:
        document_frequency.update(tokens)
    count = len(documents)
    return {
        token: math.log((count + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }


def _weighted_overlap(
    query: frozenset[str],
    document: frozenset[str],
    query_weight: float,
    token_idf: Callable[[str], float],
) -> float:
    if query_weight == 0:
        return 0.0
    return sum(token_idf(token) for token in query & document) / query_weight


def _set_coverage(
    query: frozenset[tuple[str, ...]],
    document: frozenset[tuple[str, ...]],
) -> float:
    return len(query & document) / len(query) if query else 0.0


def _heading_phrase_matches(section: str, query_tokens: tuple[str, ...]) -> bool:
    heading_tokens = _tokenize(section)
    if len(heading_tokens) < 2 or len(query_tokens) < len(heading_tokens):
        return False
    size = len(heading_tokens)
    return any(
        tuple(query_tokens[index : index + size]) == heading_tokens
        for index in range(len(query_tokens) - size + 1)
    )


__all__ = [
    "ALLOWED_POLICY_SOURCES",
    "DEFAULT_TOP_K",
    "EXACT_PHRASE_WEIGHT",
    "HEADING_WEIGHT",
    "LEXICAL_WEIGHT",
    "LocalPolicyRetriever",
    "MIN_MATCHED_QUERY_TOKENS",
    "MIN_RETRIEVAL_SCORE",
    "NGRAM_WEIGHT",
    "PolicyCorpusError",
    "PolicyEvidence",
    "RetrievalCandidate",
    "RetrievalResult",
    "load_policy_corpus",
]
