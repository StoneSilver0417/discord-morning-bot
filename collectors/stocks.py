"""주식 동향 수집기 - yfinance + FinanceDataReader + 네이버 증권 뉴스"""
import requests
from bs4 import BeautifulSoup
from config import Config
from utils.logger import setup_logger

logger = setup_logger("stocks")


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
        from datetime import datetime, timedelta

        end = datetime.now()
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
    """네이버 증권 뉴스 헤드라인을 크롤링합니다."""
    text = "\n[증권 주요 뉴스]\n"

    try:
        url = "https://finance.naver.com/news/mainnews.naver"
        resp = requests.get(url, headers=Config.HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try specific finance main news selectors first
        news_items = soup.select("dd.articleSubject a, a.articleSubject, .main_news_list a")
        
        if not news_items:
            # Fallback for search results or other structures
            news_items = soup.select("a.news_tit")
            
        if not news_items:
            # Fallback for new/dynamic classes (e.g. fender-ui)
            news_items = soup.select("a[class*='fender-ui']")
            
        headlines = []
        for item in news_items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if title and len(title) > 10:
                if href and not href.startswith("http"):
                    href = f"https://finance.naver.com{href}"
                headlines.append(f"  • {title}")
                if len(headlines) >= 10:
                    break

        if not headlines:
            # 대체: 네이버 검색 뉴스
            search_url = "https://search.naver.com/search.naver?where=news&query=증시+시황"
            resp2 = requests.get(search_url, headers=Config.HEADERS, timeout=10)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for a in soup2.select("a.news_tit")[:10]:
                title = a.get_text(strip=True)
                if title:
                    headlines.append(f"  • {title}")

        text += "\n".join(headlines) if headlines else "  뉴스를 가져올 수 없습니다."
        logger.info(f"[네이버증권] 뉴스 {len(headlines)}건 수집")

    except Exception as e:
        logger.error(f"[네이버증권] 뉴스 크롤링 실패: {e}")
        text += f"  크롤링 실패: {e}"

    return text


def collect_all_stocks() -> str:
    """모든 주식 데이터를 수집하여 텍스트로 반환합니다."""
    parts = []
    parts.append(collect_index_data())
    parts.append(collect_korean_market())
    parts.append(collect_naver_finance_news())
    return "\n".join(parts)
