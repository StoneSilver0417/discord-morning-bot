"""공무원 관련 뉴스 수집기 - Naver Open API 뉴스 검색 기반"""
import html
import re
import requests
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


def search_naver_news(keyword: str, count: int = 10) -> list[dict]:
    """Naver Open API 뉴스 검색으로 키워드 관련 뉴스를 수집합니다."""
    if not Config.NAVER_CLIENT_ID or not Config.NAVER_CLIENT_SECRET:
        logger.warning(
            "[네이버뉴스] Naver API 키 미설정 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)"
        )
        return []

    articles: list[dict] = []
    display_count = min(max(1, count), 100)
    url = (
        f"https://openapi.naver.com/v1/search/news.json"
        f"?query={requests.utils.quote(keyword)}"
        f"&display={display_count}"
        f"&sort=sim"
    )
    headers = {
        "X-Naver-Client-Id": Config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": Config.NAVER_CLIENT_SECRET,
        "User-Agent": Config.USER_AGENT,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 401:
            logger.warning(
                "[네이버뉴스] Naver API 인증 실패 (401 Unauthorized - Client ID/Secret 확인 필요)"
            )
            return []
        if resp.status_code == 403:
            logger.warning(
                "[네이버뉴스] Naver API 접근 거부 (403 Forbidden - 권한 또는 일일 한도 초과)"
            )
            return []
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])

        for item in items:
            title = _clean_text(item.get("title", ""))
            summary = _clean_text(item.get("description", ""))
            link = item.get("originallink") or item.get("link", "")
            pub_date = item.get("pubDate", "")

            if not title or not link:
                continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "pubDate": pub_date,
                "keyword": keyword,
            })

        logger.info(f"[네이버뉴스] '{keyword}' {len(articles)}건 수집")

    except (requests.RequestException, ValueError, KeyError) as e:
        logger.error(f"[네이버뉴스] '{keyword}' 검색 실패: {e}")

    return articles


def collect_all_civil_service() -> str:
    """모든 키워드에 대해 공무원 뉴스를 수집하여 텍스트형 리포트로 반환합니다."""
    all_articles: list[dict] = []
    seen_titles: set[str] = set()

    for keyword in Config.CIVIL_SERVICE_KEYWORDS:
        news = search_naver_news(keyword, count=10)
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
