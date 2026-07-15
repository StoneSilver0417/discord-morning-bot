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
            for entry in feed.entries[:5]:
                # HTML 태그 제거
                summary_raw = entry.get("summary", "")
                from bs4 import BeautifulSoup
                summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text(strip=True)
                
                articles.append({
                    "source": feed_info["name"],
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": summary_clean[:200],
                })
            logger.info(f"[RSS] {feed_info['name']}: {min(5, len(feed.entries))}건 수집")
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

    if not all_articles:
        raise RuntimeError("모든 IT 뉴스 소스에서 수집 결과가 비어 있습니다.")

    # 요약 실패 시를 대비해 전체 기사 중 상위 10개만 텍스트로 만듦 (링크 위주)
    display_articles = all_articles[:10]
    
    text = f"[IT 뉴스 수집 결과 - 총 {len(all_articles)}건 중 상위 10개]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}** ({art['source']})\n"
            f"🔗 {art['link']}\n\n"
        )
    
    return text
