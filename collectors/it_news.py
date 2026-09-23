"""IT 뉴스 수집기 - RSS + Hacker News API"""
import calendar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
import feedparser
from config import Config
from utils.article_store import ArticleStore, NoFreshArticlesError, filter_fresh
from utils.logger import setup_logger

logger = setup_logger("it_news")
ARTICLE_STORE_PATH = str(Path("data") / "article_store.json")


def _get_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_published_at(entry: dict) -> datetime | None:
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time:
        return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=timezone.utc)

    value = entry.get("published") or entry.get("pubDate") or entry.get("updated") or ""
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def collect_rss_feeds() -> list:
    """RSS 피드에서 IT 뉴스를 수집합니다."""
    articles = []

    for feed_info in Config.IT_NEWS_FEEDS:
        try:
            response = requests.get(
                feed_info["url"],
                headers=Config.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            collected_count = 0
            for entry in feed.entries[:8]:
                # HTML 태그 제거
                summary_raw = entry.get("summary", "")
                from bs4 import BeautifulSoup
                summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text(strip=True)
                
                published_at = _parse_published_at(entry)
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                if not title or not link or published_at is None:
                    continue

                articles.append({
                    "source": feed_info["name"],
                    "title": title,
                    "link": link,
                    "summary": summary_clean[:200],
                    "published_at": published_at,
                })
                collected_count += 1
            logger.info(f"[RSS] {feed_info['name']}: {collected_count}건 수집")
        except Exception as e:  # noqa: BROAD_EXCEPT_OK - isolate third-party feed failures
            logger.warning(f"[RSS] {feed_info['name']} 실패: {e}")

    return articles


def collect_hackernews() -> list:
    """Hacker News Top Stories를 수집합니다."""
    articles = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10,
        )
        story_ids = resp.json()[:20]

        for sid in story_ids:
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5,
                ).json()
                if item and item.get("title") and item.get("time") is not None:
                    articles.append({
                        "source": "HackerNews",
                        "title": item["title"],
                        "link": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "summary": f"Points: {item.get('score', 0)}, Comments: {item.get('descendants', 0)}",
                        "published_at": datetime.fromtimestamp(
                            item["time"], tz=timezone.utc
                        ),
                    })
            except Exception:  # noqa: BROAD_EXCEPT_OK - one bad HN item must not abort the batch
                continue

        logger.info(f"[HackerNews] {len(articles)}건 수집")
    except Exception as e:  # noqa: BROAD_EXCEPT_OK - external API boundary
        logger.error(f"[HackerNews] 수집 실패: {e}")

    return articles


def collect_all_it_news() -> str:
    """모든 IT 뉴스를 수집하여 텍스트로 반환합니다."""
    rss_articles = collect_rss_feeds()
    hn_articles = collect_hackernews()

    all_articles = rss_articles + hn_articles

    if not all_articles:
        raise NoFreshArticlesError("새로운 IT 뉴스가 없습니다.")

    dated_articles = [article for article in all_articles if "published_at" in article]
    undated_articles = [article for article in all_articles if "published_at" not in article]

    now = _get_now()
    store = ArticleStore(ARTICLE_STORE_PATH)
    store.prune(now=now)

    fresh_articles = filter_fresh(
        dated_articles,
        store,
        "it_news",
        now=now,
        max_age_hours=24,
    )
    fresh_articles.extend(undated_articles)

    if not fresh_articles:
        raise NoFreshArticlesError("새로운 IT 뉴스가 없습니다.")

    fresh_articles.sort(
        key=lambda article: article.get("published_at")
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    source_counts: dict[str, int] = {}
    display_articles: list[dict] = []
    for article in fresh_articles:
        source = article["source"]
        if source_counts.get(source, 0) < 5:
            display_articles.append(article)
            source_counts[source] = source_counts.get(source, 0) + 1
        if len(display_articles) >= 20:
            break

    for article in display_articles:
        store.mark_seen("it_news", article["link"], now)
    store.save()

    text = f"[IT 뉴스 수집 결과 - 총 {len(display_articles)}건]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}** ({art['source']})\n"
            f"설명: {art.get('summary') or '기사 설명 없음'}\n"
            f"🔗 {art['link']}\n\n"
        )
    
    return text
