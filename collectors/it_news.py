"""IT 뉴스 수집기 - RSS + Hacker News API"""
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


def collect_rss_feeds() -> list:
    """RSS 피드에서 IT 뉴스를 수집합니다."""
    articles = []

    for feed_info in Config.IT_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            collected_count = 0
            for entry in feed.entries[:5]:
                # HTML 태그 제거
                summary_raw = entry.get("summary", "")
                from bs4 import BeautifulSoup
                summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text(strip=True)
                
                published_at = _parse_published_at(
                    entry.get("published", entry.get("pubDate", ""))
                )
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
        except Exception as e:
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
        story_ids = resp.json()[:10]

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
            except Exception:
                continue

        logger.info(f"[HackerNews] {len(articles)}건 수집")
    except Exception as e:
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
    if dated_articles:
        now = _get_now()
        store = ArticleStore(ARTICLE_STORE_PATH)
        store.prune(now=now)
        all_articles = filter_fresh(dated_articles, store, "it_news", now=now)
        if not all_articles:
            raise NoFreshArticlesError("새로운 IT 뉴스가 없습니다.")
        for article in all_articles:
            store.mark_seen("it_news", article["link"], now)
        store.save()

    # 요약 실패 시를 대비해 전체 기사 중 상위 10개만 텍스트로 만듦 (링크 위주)
    display_articles = all_articles[:10]
    
    text = f"[IT 뉴스 수집 결과 - 총 {len(all_articles)}건 중 상위 10개]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}** ({art['source']})\n"
            f"설명: {art.get('summary') or '기사 설명 없음'}\n"
            f"🔗 {art['link']}\n\n"
        )
    
    return text
