"""공무원 관련 뉴스 수집기 - 네이버 뉴스 검색 기반"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from config import Config
from utils.logger import setup_logger

logger = setup_logger("civil_service")

_UI_SUFFIX = "새 창 열림"  # 네이버가 접근성을 위해 링크 텍스트 끝에 숨겨서 붙이는 문구


def _extract_articles(soup: BeautifulSoup) -> list:
    """네이버 뉴스 검색 결과 HTML에서 제목/링크/설명을 추출합니다.

    네이버가 배포마다 클래스명을 해시로 바꿔서 `a.news_tit` 같은 고정 셀렉터가
    깨지는 경우가 있다. 이때는 실제 기사 링크(경로가 언론사 홈 루트가 아니고
    keep.naver.com도 아닌 링크)만 href로 그룹핑해, 같은 href의 첫 텍스트를
    제목(끝의 "새 창 열림" 문구 제거), 두 번째 텍스트를 설명으로 취급한다.
    """
    news_items = soup.select("a.news_tit")
    if news_items:
        articles = []
        for item in news_items:
            title = item.get_text(strip=True)
            link = item.get("href", "")
            if title:
                articles.append({"title": title, "link": link, "summary": ""})
        descs = soup.select("div.news_dsc, a.api_txt_lines.dsc_txt_wrap")
        for i, desc in enumerate(descs[:len(articles)]):
            articles[i]["summary"] = desc.get_text(strip=True)[:150]
        return articles

    grouped: dict[str, list] = {}
    order = []
    for a in soup.select("a[class*='fender-ui']"):
        href = a.get("href", "")
        if not href or href == "#" or href.startswith("javascript:"):
            continue
        if "keep.naver.com" in href or "media.naver.com/press" in href:
            continue  # Keep 저장 버튼, 언론사 배지 링크 등 기사 본문이 아닌 UI 요소 제외
        parsed = urlparse(href)
        if (not parsed.path or parsed.path == "/") and not parsed.query:
            continue  # 언론사 홈페이지 링크 등 기사 본문이 아닌 UI 요소 제외
        text = a.get_text(strip=True).replace(_UI_SUFFIX, "").strip()
        if not text or text == "네이버뉴스":
            continue
        if href not in grouped:
            grouped[href] = []
            order.append(href)
        grouped[href].append(text)

    articles = []
    for href in order:
        texts = grouped[href]
        if len(texts) < 2:
            continue  # 제목만 있고 설명이 없는 그룹은 대부분 배지·버튼류 UI 요소
        articles.append({"title": texts[0], "link": href, "summary": texts[1][:150]})
    return articles


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

        for art in _extract_articles(soup):
            art["keyword"] = keyword
            articles.append(art)
            if len(articles) >= count:
                break

        logger.info(f"[네이버뉴스] '{keyword}' {len(articles)}건 수집")

    except Exception as e:
        logger.error(f"[네이버뉴스] '{keyword}' 검색 실패: {e}")

    return articles


def collect_all_civil_service() -> str:
    """모든 키워드에 대해 공무원 뉴스를 수집하여 텍스트로 반환합니다."""
    all_articles = []
    seen_titles = set()

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        news = search_naver_news(keyword, count=5)
        for item in news:
            title = item["title"]
            if title not in seen_titles:
                all_articles.append(item)
                seen_titles.add(title)

    if not all_articles:
        raise RuntimeError("모든 공무원 뉴스 검색 결과가 비어 있습니다.")
    
    # 요약 실패 시를 대비해 상위 10개만 텍스트로 변환 (링크 위주)
    display_articles = all_articles[:10]
    
    text = f"[공무원 관련 뉴스 - 총 {len(all_articles)}건 중 상위 10개]\n\n"
    for i, art in enumerate(display_articles, 1):
        text += (
            f"{i}. **{art['title']}**\n"
            f"설명: {art.get('summary') or '기사 설명 없음'}\n"
            f"🔗 {art['link']}\n\n"
        )
    
    return text
