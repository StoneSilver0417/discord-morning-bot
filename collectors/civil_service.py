"""공무원 관련 뉴스 수집기 - 네이버 뉴스 검색 기반"""
import requests
from bs4 import BeautifulSoup
from config import Config
from utils.logger import setup_logger

logger = setup_logger("civil_service")


def search_naver_news(keyword: str, count: int = 5) -> list:
    """네이버 뉴스 검색으로 키워드 관련 뉴스를 수집합니다."""
    articles = []
    try:
        url = (
            f"https://search.naver.com/search.naver"
            f"?where=news&query={requests.utils.quote(keyword)}"
            f"&sort=1"  # 최신순
        )
        resp = requests.get(url, headers=Config.HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        news_items = soup.select("a.news_tit")
        if not news_items:
            # Fallback for dynamic classes
            news_items = soup.select("a[class*='fender-ui']")

        for item in news_items:
            title = item.get_text(strip=True)
            link = item.get("href", "")
            if title and len(title) > 15: # Headlines are usually substantial
                articles.append({
                    "keyword": keyword,
                    "title": title,
                    "link": link,
                })
                if len(articles) >= count:
                    break

        # 뉴스 요약(description)도 수집
        descs = soup.select("div.news_dsc, a.api_txt_lines.dsc_txt_wrap")
        for i, desc in enumerate(descs[:len(articles)]):
            if i < len(articles):
                articles[i]["summary"] = desc.get_text(strip=True)[:150]

        logger.info(f"[네이버뉴스] '{keyword}' {len(articles)}건 수집")

    except Exception as e:
        logger.error(f"[네이버뉴스] '{keyword}' 검색 실패: {e}")

    return articles


def collect_all_civil_service() -> str:
    """모든 공무원 관련 뉴스를 수집하여 텍스트로 반환합니다."""
    all_articles = []
    seen_titles = set()

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        articles = search_naver_news(keyword, count=5)
        for art in articles:
            # 중복 제거
            if art["title"] not in seen_titles:
                seen_titles.add(art["title"])
                all_articles.append(art)

    text = f"[공무원 관련 뉴스 - 총 {len(all_articles)}건]\n\n"
    for i, art in enumerate(all_articles, 1):
        text += (
            f"{i}. [검색어: {art['keyword']}] {art['title']}\n"
            f"   링크: {art['link']}\n"
        )
        if art.get("summary"):
            text += f"   내용: {art['summary']}\n"
        text += "\n"

    return text
