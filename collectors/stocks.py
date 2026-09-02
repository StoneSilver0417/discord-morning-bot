"""주식 동향 수집기 - yfinance + FinanceDataReader + Google News RSS"""
import html
import re
import urllib.parse
import feedparser
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


def collect_stock_news(query: str = "증시 시황") -> str:
    """Google News RSS를 통해 증권/시황 뉴스를 수집합니다."""
    text = "\n[증권 주요 뉴스]\n"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(
                f"[증권뉴스] RSS 파싱 실패 또는 빈 결과: {feed.get('bozo_exception')}"
            )
            return text + "  뉴스를 가져올 수 없습니다."

        headlines: list[str] = []
        seen_titles: set[str] = set()

        for item in feed.entries:
            title = _clean_text(item.get("title", ""))
            summary = _clean_text(item.get("summary", item.get("description", "")))
            link = item.get("link", "")

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
            logger.info(f"[증권뉴스] 뉴스 {len(headlines)}건 수집 완료")
        else:
            text += "  뉴스를 가져올 수 없습니다."
            logger.warning("[증권뉴스] 수집된 뉴스가 없습니다.")

    except Exception as e:
        logger.error(f"[증권뉴스] 뉴스 수집 실패: {e}")
        text += f"  뉴스 수집 실패: {e}"

    return text


collect_naver_finance_news = collect_stock_news


def collect_all_stocks() -> str:
    """모든 주식 데이터를 수집하여 텍스트로 반환합니다."""
    parts = []
    parts.append(collect_index_data())
    parts.append(collect_korean_market())
    parts.append(collect_stock_news())
    return "\n".join(parts)
