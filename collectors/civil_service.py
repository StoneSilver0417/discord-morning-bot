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
    """모든 키워드에 대해 공무원 뉴스를 수집하여 텍스트로 반환합니다."""
    all_articles = []
    seen_titles = set()

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        news = search_naver_news(keyword, count=3)
        for item in news:
            title = item["title"]
            if title not in seen_titles:
                all_articles.append(item)
                seen_titles.add(title)
    
    # 요약 실패 시를 대비해 상위 10개만 텍스트로 변환
    display_articles = all_articles[:10]
    
    text = f"[공무원 관련 뉴스 - 총 {len(all_articles)}건 중 상위 10개]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}**\n"
            f"🔗 {art['link']}\n\n"
        )
        if art.get("summary"):
            text += f"   내용: {art['summary']}\n"
        text += "\n"
    
    return text
