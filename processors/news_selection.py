import re
import unicodedata
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

NEWS_LIMIT: Final = 10
_BLOCK_PATTERN: Final = re.compile(
    r"(?ms)^\s*(\d+)[.)]\s+(.*?)(?=^\s*\d+[.)]\s+|\Z)"
)
_URL_PATTERN: Final = re.compile(r"https?://[^\s<>]+")
_TRACKING_PARAMETERS: Final = frozenset({"fbclid", "gclid"})


@dataclass(frozen=True, slots=True)
class NewsCandidate:
    title: str
    canonical_url: str
    body: str


@dataclass(frozen=True, slots=True)
class NewsSelectionContract:
    candidates: tuple[NewsCandidate, ...]
    target_count: int
    fallback_text: str
    permitted_urls: frozenset[str]


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url.rstrip(".,"))
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in _TRACKING_PARAMETERS
        ],
        doseq=True,
    )
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, query, "")
    )


def _normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title)
    normalized = re.sub(r"[*_`#]", "", normalized)
    normalized = re.sub(r"^\s*(?:\[[^]]+\]\s*)+", "", normalized)
    return " ".join(normalized.casefold().split())


def _candidate_title(title_line: str) -> str:
    bold_title = re.match(r"^\s*\*\*(.+?)\*\*", title_line)
    return _normalize_title(bold_title.group(1) if bold_title else title_line)


def _parse_candidates(raw_data: str) -> tuple[NewsCandidate, ...]:
    candidates: list[NewsCandidate] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()

    for _, body in _BLOCK_PATTERN.findall(raw_data):
        clean_body = body.strip()
        lines = clean_body.splitlines()
        urls = _URL_PATTERN.findall(clean_body)
        if not lines or not urls:
            continue

        normalized_title = _candidate_title(lines[0])
        canonical_url = _canonicalize_url(urls[-1])
        if not normalized_title or normalized_title in seen_titles:
            continue
        if canonical_url in seen_urls:
            continue

        candidates.append(
            NewsCandidate(
                title=normalized_title,
                canonical_url=canonical_url,
                body=clean_body,
            )
        )
        seen_titles.add(normalized_title)
        seen_urls.add(canonical_url)

    return tuple(candidates)


def build_news_contract(raw_data: str) -> NewsSelectionContract:
    candidates = _parse_candidates(raw_data)
    selected = candidates[:NEWS_LIMIT]
    if selected:
        rendered = "\n\n".join(
            f"{index}. {candidate.body}" for index, candidate in enumerate(selected, 1)
        )
        fallback_text = f"[뉴스 선별 결과 - 총 {len(selected)}건]\n\n{rendered}"
    else:
        fallback_text = "[뉴스 선별 결과 - 총 0건]"

    return NewsSelectionContract(
        candidates=candidates,
        target_count=min(NEWS_LIMIT, len(candidates)),
        fallback_text=fallback_text,
        permitted_urls=frozenset(candidate.canonical_url for candidate in candidates),
    )


def is_valid_news_selection(
    result: str,
    contract: NewsSelectionContract,
) -> bool:
    first_block = _BLOCK_PATTERN.search(result)
    if first_block is None or result[: first_block.start()].strip():
        return False
    blocks = _BLOCK_PATTERN.findall(result)
    if contract.target_count == 0 or len(blocks) != contract.target_count:
        return False
    if [int(number) for number, _ in blocks] != list(
        range(1, contract.target_count + 1)
    ):
        return False

    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    priority_ranks: list[int] = []
    priority_values = {"상": 3, "중": 2, "하": 1}
    for _, body in blocks:
        lines = body.strip().splitlines()
        urls = _URL_PATTERN.findall(body)
        link_lines = re.findall(r"(?m)^\s*🔗\s*(https?://\S+)\s*$", body)
        summary = re.search(
            r"(?m)^\s*[•\-*]\s*내용\s*요약\s*:[ \t]*([^ \t\r\n].*)$",
            body,
        )
        impact = re.search(
            r"(?m)^\s*[•\-*]\s*실무[/\s]*영향\s*:[ \t]*([^ \t\r\n].*)$",
            body,
        )
        priority = re.match(
            r"^\s*\[(?:우선순위\s*:\s*)?(상|중|하)\]\s+",
            lines[0] if lines else "",
        )
        if (
            not lines
            or len(urls) != 1
            or len(link_lines) != 1
            or re.fullmatch(r"🔗\s*https?://\S+", lines[-1].strip()) is None
            or not summary
            or not impact
            or not priority
        ):
            return False

        title = _normalize_title(lines[0])
        canonical_url = _canonicalize_url(urls[0])
        if not title or title in seen_titles or canonical_url in seen_urls:
            return False
        if canonical_url not in contract.permitted_urls:
            return False
        candidate = next(
            item for item in contract.candidates if item.canonical_url == canonical_url
        )
        if title != candidate.title and not title.startswith(f"{candidate.title} ("):
            return False
        seen_titles.add(title)
        seen_urls.add(canonical_url)
        priority_ranks.append(priority_values[priority.group(1)])

    return all(
        higher >= lower
        for higher, lower in zip(priority_ranks, priority_ranks[1:])
    )
