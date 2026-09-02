"""주식 동향 수집기 - yfinance + FinanceDataReader + 네이버 증권 뉴스 (Naver Open API)"""
import html
import re
import requests
from config import Config
from utils.logger import setup_logger

logger = setup_logger("stocks")


def _clean_text(raw_text: str) -> str:
    """HTML 특수문자 엔티티 및 태그를 완벽히 제거하고 공백을 정돈합니다."""
    if not raw_text:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", raw_text)
    unescaped = html.unescape(no_tags)
    return " ".join(unescaped.split()).strip()


def collect_index_data() -> str:
    """주요 지수 데이터를 yfinance로 수집합니다."""
    text = "[주요 지수 현황]\n"

    try:
        import yfinance as yf

        for name, ticker in Config.STOCK_INDICES.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if len(hist) >= 2:
                    today = hist.iloc[-1]["Close"]
                    yesterday = hist.iloc[-2]["Close"]
                    change = today - yesterday
                    change_pct = (change / yesterday) * 100
                    arrow = "▲" if change > 0 else "▼" if change < 0 else "→"
                    text += (
                        f"  {name}: {today:,.2f} "
                        f"{arrow} {abs(change):,.2f} ({change_pct:+.2f}%)\n"
                    )
                elif len(hist) == 1:
                    today = hist.iloc[-1]["Close"]
                    text += f"  {name}: {today:,.2f}\n"
            except Exception as e:
                logger.warning(f"[yfinance] {name} 수집 실패: {e}")
                text += f"  {name}: 데이터 없음\n"

    except ImportError:
        logger.error("yfinance 라이브러리가 설치되지 않았습니다.")
        text += "  (yfinance 미설치)\n"

    return text


def collect_korean_market() -> str:
    """FinanceDataReader로 한국 시장 추가 데이터를 수집합니다."""
    text = "\n[한국 시장 상세]\n"

    try:
        import FinanceDataReader as fdr
        from utils.time_utils import get_kst_now
        from datetime import timedelta

        end = get_kst_now()
        start = end - timedelta(days=7)
        start_str = start.strftime("%Y-%m-%d")

        # 거래량 상위 종목 등 추가 정보
        try:
            krx = fdr.StockListing("KRX")
            if krx is not None and len(krx) > 0:
                # 시가총액 상위 10개 종목 변동률
                if "Marcap" in krx.columns:
                    top10 = krx.nlargest(10, "Marcap")
                    text += "  시가총액 상위 10 종목:\n"
                    for _, row in top10.iterrows():
                        name = row.get("Name", "N/A")
                        chg = row.get("ChagesRatio", row.get("Changes", "N/A"))
                        text += f"    {name}: {chg}%\n"
        except Exception as e:
            logger.warning(f"[FDR] KRX 데이터 수집 실패: {e}")

    except ImportError:
        logger.warning("FinanceDataReader 미설치 - 건너뜀")

    return text


def collect_naver_finance_news() -> str:
    """Naver Open API를 통해 증권/시황 뉴스를 수집합니다."""
    text = "\n[증권 주요 뉴스]\n"

    if not Config.NAVER_CLIENT_ID or not Config.NAVER_CLIENT_SECRET:
        logger.warning(
            "[네이버뉴스] Naver API 키 미설정 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)"
        )
        return text + "  (Naver API 키 미설정으로 뉴스 수집 생략)"

    query = "증시 시황"
    url = (
        f"https://openapi.naver.com/v1/search/news.json"
        f"?query={requests.utils.quote(query)}"
        f"&display=15"
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
            return text + "  (Naver API 인증 실패)"
        if resp.status_code == 403:
            logger.warning(
                "[네이버뉴스] Naver API 접근 거부 (403 Forbidden - 권한 또는 일일 한도 초과)"
            )
            return text + "  (Naver API 접근 거부)"
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])

        headlines: list[str] = []
        seen_titles: set[str] = set()

        for item in items:
            title = _clean_text(item.get("title", ""))
            summary = _clean_text(item.get("description", ""))
            link = item.get("originallink") or item.get("link", "")

            if not title or not link or len(title) < 5:
                continue

            if title in seen_titles:
                continue
            seen_titles.add(title)

            if summary:
                headlines.append(f"  • {title}\n    설명: {summary}\n    🔗 {link}")
            else:
                headlines.append(f"  • {title}\n    🔗 {link}")

            if len(headlines) >= 10:
                break

        if headlines:
            text += "\n".join(headlines)
            logger.info(f"[네이버증권] 뉴스 {len(headlines)}건 수집 완료")
        else:
            text += "  뉴스를 가져올 수 없습니다."
            logger.warning("[네이버증권] 수집된 뉴스가 없습니다.")

    except Exception as e:
        logger.error(f"[네이버증권] 뉴스 수집 실패: {e}")
        text += f"  뉴스 수집 실패: {e}"

    return text


def collect_all_stocks() -> str:
    """모든 주식 데이터를 수집하여 텍스트로 반환합니다."""
    parts = []
    parts.append(collect_index_data())
    parts.append(collect_korean_market())
    parts.append(collect_naver_finance_news())
    return "\n".join(parts)
