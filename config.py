"""설정 관리 모듈"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """환경변수 및 상수 설정"""

    # Discord Webhooks
    DISCORD_WEBHOOK_MAIN = os.getenv("DISCORD_WEBHOOK_MAIN", "")
    DISCORD_WEBHOOK_WEATHER = os.getenv("DISCORD_WEBHOOK_WEATHER", "")
    DISCORD_WEBHOOK_STOCKS = os.getenv("DISCORD_WEBHOOK_STOCKS", "")
    DISCORD_WEBHOOK_IT_NEWS = os.getenv("DISCORD_WEBHOOK_IT_NEWS", "")
    DISCORD_WEBHOOK_CIVIL_SERVICE = os.getenv("DISCORD_WEBHOOK_CIVIL_SERVICE", "")

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # 날씨 지역 설정
    WEATHER_LOCATIONS = [
        {"name": "경산 중방동", "query": "경산 중방동 날씨"},
        {"name": "대구 만촌동", "query": "대구 만촌동 날씨"},
    ]

    # 주식 관련
    STOCK_INDICES = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "USD/KRW": "KRW=X",
        "BTC/USD": "BTC-USD",
    }

    # IT 뉴스 RSS 피드
    IT_NEWS_FEEDS = [
        {"name": "GeekNews", "url": "https://news.hada.io/rss/news"},
        {"name": "요즘IT", "url": "https://yozm.wishket.com/magazine/feed/"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "44bits", "url": "https://www.44bits.io/ko/feed.xml"},
    ]

    # 공무원 뉴스 검색 키워드
    CIVIL_SERVICE_KEYWORDS = [
        "공무원 정책",
        "공무원 처우",
        "공무원 급여",
        "공무원 연금",
        "공무원 채용",
        "지방직 공무원",
        "국가직 공무원",
        "전산직 공무원",
        "사회복지직 공무원",
    ]

    # 크롤링 User-Agent
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    HEADERS = {"User-Agent": USER_AGENT}
