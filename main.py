"""모닝브리핑 디스코드 봇 - 메인 엔트리포인트

GitHub Actions cron 또는 로컬에서 실행하여
날씨/주식/IT뉴스/공무원 정보를 수집 → Gemini로 가공 → Discord Webhook 전송
"""
import time
from datetime import datetime

from config import Config
from collectors.weather import collect_all_weather
from collectors.stocks import collect_all_stocks
from collectors.it_news import collect_all_it_news
from collectors.civil_service import collect_all_civil_service
from processors.gemini_processor import process_with_gemini, add_windy_links
from formatters.discord_formatter import create_embed, send_webhook
from utils.logger import setup_logger

logger = setup_logger("main")


def run_briefing():
    """전체 모닝 브리핑을 실행합니다."""
    today = datetime.now().strftime("%Y.%m.%d (%a)")
    logger.info(f"=== 모닝 브리핑 시작: {today} ===")

    # 웹훅 설정 확인 (최소 하나는 있어야 함)
    if not any([
        Config.DISCORD_WEBHOOK_MAIN,
        Config.DISCORD_WEBHOOK_WEATHER,
        Config.DISCORD_WEBHOOK_STOCKS,
        Config.DISCORD_WEBHOOK_IT_NEWS,
        Config.DISCORD_WEBHOOK_CIVIL_SERVICE
    ]):
        logger.error("설정된 디스코드 웹훅이 없습니다! .env 파일을 확인하세요.")
        return

    results = {}

    # 1. 날씨 수집 + 가공
    logger.info("📡 [1/4] 날씨 정보 수집 중...")
    try:
        weather_raw = collect_all_weather()
        weather_summary = process_with_gemini("weather", weather_raw)
        results["weather"] = add_windy_links(weather_summary)
    except Exception as e:
        logger.error(f"날씨 수집 실패: {e}")
        results["weather"] = f"날씨 정보를 가져올 수 없습니다. ({e})"
    time.sleep(2)  # API 호출 간격

    # 2. 주식 동향 수집 + 가공
    logger.info("📡 [2/4] 주식 동향 수집 중...")
    try:
        stocks_raw = collect_all_stocks()
        results["stocks"] = process_with_gemini("stocks", stocks_raw)
    except Exception as e:
        logger.error(f"주식 수집 실패: {e}")
        results["stocks"] = f"주식 정보를 가져올 수 없습니다. ({e})"
    time.sleep(2)

    # 3. IT 뉴스 수집 + 가공
    logger.info("📡 [3/4] IT 뉴스 수집 중...")
    try:
        it_raw = collect_all_it_news()
        results["it_news"] = process_with_gemini("it_news", it_raw)
    except Exception as e:
        logger.error(f"IT뉴스 수집 실패: {e}")
        results["it_news"] = f"IT 뉴스를 가져올 수 없습니다. ({e})"
    time.sleep(2)

    # 4. 공무원 뉴스 수집 + 가공
    logger.info("📡 [4/4] 공무원 뉴스 수집 중...")
    try:
        civil_raw = collect_all_civil_service()
        results["civil_service"] = process_with_gemini("civil_service", civil_raw)
    except Exception as e:
        logger.error(f"공무원뉴스 수집 실패: {e}")
        results["civil_service"] = f"공무원 관련 뉴스를 가져올 수 없습니다. ({e})"
    time.sleep(2)

    # 5. 디스코드 전송 (채널 분리)
    logger.info("📤 카테고리별 디스코드 전송 중...")

    # 매핑 설정 (카테고리: (텍스트, 웹훅URL, 제목))
    webhook_mapping = {
        "weather": (results["weather"], Config.DISCORD_WEBHOOK_WEATHER, "🌤️ 기상 정보"),
        "stocks": (results["stocks"], Config.DISCORD_WEBHOOK_STOCKS, "📈 주식 및 금융 동향"),
        "it_news": (results["it_news"], Config.DISCORD_WEBHOOK_IT_NEWS, "💻 IT/기술 뉴스"),
        "civil_service": (results["civil_service"], Config.DISCORD_WEBHOOK_CIVIL_SERVICE, "🏛️ 공무원 소식"),
    }

    for key, (content, url, title) in webhook_mapping.items():
        # 전용 웹훅이 없으면 MAIN 웹훅으로 전송
        target_url = url if url else Config.DISCORD_WEBHOOK_MAIN
        
        if target_url:
            # 카테고리별로 색상 다르게 설정 (summary: blue, others: green)
            color = "blue" if key == "summary" else "green"
            embed = create_embed(category=key, title=f"{title} | {today}", description=content)
            send_webhook(target_url, embeds=[embed])
            logger.info(f"[{key}] 전송 완료")
            time.sleep(1)  # 전송 간격

    logger.info("✅ 모든 채널로 브리핑 전송 완료!")
    return True


if __name__ == "__main__":
    run_briefing()
