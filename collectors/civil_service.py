"""공무원 관련 뉴스 수집기 - Google News RSS 기반"""
import difflib
import html
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
from config import Config
from utils.article_store import ArticleStore, NoFreshArticlesError, filter_fresh
from utils.logger import setup_logger

logger = setup_logger("civil_service")
ARTICLE_STORE_PATH = str(Path("data") / "article_store.json")


def _get_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_published_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_text(raw_text: str) -> str:
    """HTML 특수문자 엔티티 및 태그를 완벽히 제거하고 공백을 정돈합니다."""
    if not raw_text:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", raw_text)
    unescaped = html.unescape(no_tags)
    return " ".join(unescaped.split()).strip()


_CIVIL_SERVICE_TERMS = (
    "공무원",
    "공무직",
    "공시생",
    "공직사회",
    "국가직",
    "사회복지직",
    "인사혁신처",
    "전산직",
    "지방직",
)


def _normalize_for_similarity(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", _clean_text(text)).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


def _title_without_publisher(title: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,40}$", "", title).strip()


def _is_similar(left: str, right: str, threshold: float) -> bool:
    normalized_left = _normalize_for_similarity(left)
    normalized_right = _normalize_for_similarity(right)
    if not normalized_left or not normalized_right:
        return False

    left_numbers = set(re.findall(r"\d+", normalized_left))
    right_numbers = set(re.findall(r"\d+", normalized_right))
    if left_numbers and right_numbers and left_numbers != right_numbers:
        return False

    return difflib.SequenceMatcher(
        None,
        normalized_left,
        normalized_right,
    ).ratio() >= threshold


def _is_relevant(article: dict) -> bool:
    text = unicodedata.normalize(
        "NFKC",
        f'{article.get("title", "")} {article.get("summary", "")}',
    )
    return any(term in text for term in _CIVIL_SERVICE_TERMS)


def _articles_are_duplicates(left: dict, right: dict) -> bool:
    left_title = _title_without_publisher(left.get("title", ""))
    right_title = _title_without_publisher(right.get("title", ""))
    if _normalize_for_similarity(left_title) == _normalize_for_similarity(right_title):
        return True
    if _is_similar(left_title, right_title, 0.90):
        return True

    left_summary = left.get("summary", "")
    right_summary = right.get("summary", "")
    if _is_similar(left_title, right_title, 0.70):
        if _is_similar(left_summary, right_summary, 0.60):
            return True

    return _is_similar(
        f"{left_title} {left_summary}",
        f"{right_title} {right_summary}",
        0.82,
    )


def _deduplicate_articles(articles: list[dict]) -> list[dict]:
    groups: list[list[dict]] = []
    for article in articles:
        for group in groups:
            if _articles_are_duplicates(article, group[0]):
                group.append(article)
                break
        else:
            groups.append([article])

    deduped: list[dict] = []
    minimum_date = datetime.min.replace(tzinfo=timezone.utc)
    for group in groups:
        group.sort(
            key=lambda article: (
                article.get("published_at", minimum_date),
                len(article.get("summary", ""))
                if "published_at" in article
                else 0,
            ),
            reverse=True,
        )
        deduped.append(group[0])

    return deduped


def search_civil_service_news(keyword: str, count: int = 10) -> list[dict]:
    """Google News RSS로 키워드 관련 공무원 뉴스를 수집합니다."""
    articles: list[dict] = []
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(
                f"[공무원뉴스] '{keyword}' RSS 파싱 실패 또는 빈 결과: {feed.get('bozo_exception')}"
            )
            return []

        for entry in feed.entries[:count]:
            title = _clean_text(entry.get("title", ""))
            summary = _clean_text(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")
            pub_date = entry.get("published", entry.get("pubDate", ""))
            published_at = _parse_published_at(pub_date)

            if not title or not link or published_at is None:
                continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "pubDate": pub_date,
                "keyword": keyword,
                "published_at": published_at,
            })

        logger.info(f"[공무원뉴스] '{keyword}' {len(articles)}건 수집")

    except Exception as e:  # noqa: BROAD_EXCEPT_OK - external RSS boundary
        logger.error(f"[공무원뉴스] '{keyword}' 검색 실패: {e}")

    return articles


search_naver_news = search_civil_service_news
search_google_news = search_civil_service_news


def collect_all_civil_service() -> str:
    """모든 키워드에 대해 공무원 뉴스를 수집하여 텍스트형 리포트로 반환합니다."""
    all_articles: list[dict] = []

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        news = search_civil_service_news(keyword, count=10)
        for item in news:
            title = item.get("title", "")
            if not title or len(title) < 5:
                continue
            if not _is_relevant(item):
                continue
            all_articles.append(item)

    if not all_articles:
        raise NoFreshArticlesError("새로운 공무원 뉴스가 없습니다.")

    all_articles = _deduplicate_articles(all_articles)

    dated_articles = [article for article in all_articles if "published_at" in article]
    if dated_articles:
        now = _get_now()
        store = ArticleStore(ARTICLE_STORE_PATH)
        store.prune(now=now)

        fresh_articles = filter_fresh(dated_articles, store, "civil_service", now=now)
        if not fresh_articles:
            raise NoFreshArticlesError("새로운 공무원 뉴스가 없습니다.")
        all_articles = fresh_articles

    all_articles.sort(
        key=lambda article: article.get(
            "published_at",
            datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    display_articles = all_articles[:15]

    if dated_articles:
        for article in display_articles:
            store.mark_seen("civil_service", article["link"], now)
        store.save()

    text = f"[공무원 관련 뉴스 수집 결과 - 총 {len(all_articles)}건 중 후보 {len(display_articles)}건]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}**\n"
            f"설명: {art.get('summary') or '기사 설명 없음'}\n"
            f"🔗 {art['link']}\n\n"
        )

    return text
