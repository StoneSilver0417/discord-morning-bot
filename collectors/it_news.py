"""IT 뉴스 수집기 - RSS + Hacker News API"""
import requests
import feedparser
from config import Config
from utils.logger import setup_logger

logger = setup_logger("it_news")


def collect_rss_feeds() -> list:
    """RSS 피드에서 IT 뉴스를 수집합니다."""
    articles = []

    for feed_info in Config.IT_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:7]:
                articles.append({
                    "source": feed_info["name"],
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:200].strip(),
                })
            logger.info(f"[RSS] {feed_info['name']}: {min(7, len(feed.entries))}건 수집")
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
                if item and item.get("title"):
                    articles.append({
                        "source": "HackerNews",
                        "title": item["title"],
                        "link": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "summary": f"Points: {item.get('score', 0)}, Comments: {item.get('descendants', 0)}",
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

    text = f"[IT 뉴스 수집 결과 - 총 {len(all_articles)}건]\n\n"
    for i, art in enumerate(all_articles, 1):
        text += (
            f"{i}. [{art['source']}] {art['title']}\n"
            f"   링크: {art['link']}\n"
            f"   요약: {art['summary']}\n\n"
        )

    return text
