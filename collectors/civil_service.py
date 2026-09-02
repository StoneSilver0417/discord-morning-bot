"""공무원 관련 뉴스 수집기 - Google News RSS 기반"""
import html
import re
import urllib.parse
import feedparser
from config import Config
from utils.logger import setup_logger

logger = setup_logger("civil_service")


def _clean_text(raw_text: str) -> str:
    """HTML 특수문자 엔티티 및 태그를 완벽히 제거하고 공백을 정돈합니다."""
    if not raw_text:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", raw_text)
    unescaped = html.unescape(no_tags)
    return " ".join(unescaped.split()).strip()


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

            if not title or not link:
                continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "pubDate": pub_date,
                "keyword": keyword,
            })

        logger.info(f"[공무원뉴스] '{keyword}' {len(articles)}건 수집")

    except Exception as e:
        logger.error(f"[공무원뉴스] '{keyword}' 검색 실패: {e}")

    return articles


search_naver_news = search_civil_service_news
search_google_news = search_civil_service_news


def collect_all_civil_service() -> str:
    """모든 키워드에 대해 공무원 뉴스를 수집하여 텍스트형 리포트로 반환합니다."""
    all_articles: list[dict] = []
    seen_titles: set[str] = set()

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        news = search_civil_service_news(keyword, count=10)
        for item in news:
            title = item.get("title", "")
            if not title or len(title) < 5:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            all_articles.append(item)

    if not all_articles:
        raise RuntimeError("모든 공무원 뉴스 검색 결과가 비어 있습니다.")

    # 설명이 있는 기사를 우선 순위로 정렬하고 최대 25~30건까지 수집
    prioritized = sorted(
        all_articles,
        key=lambda a: 0 if a.get("summary") else 1,
    )
    display_articles = prioritized[:25]

    text = f"[공무원 관련 뉴스 수집 결과 - 총 {len(all_articles)}건 중 후보 {len(display_articles)}건]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}**\n"
            f"설명: {art.get('summary') or '기사 설명 없음'}\n"
            f"🔗 {art['link']}\n\n"
        )

    return text
