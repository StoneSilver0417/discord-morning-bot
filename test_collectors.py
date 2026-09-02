"""
수집기 단독 테스트 스크립트 (날씨, 주식, IT뉴스, 공무원뉴스 수집 확인)

실행: python test_collectors.py (또는 py test_collectors.py)
"""
import time
from config import Config


def test_weather():
    print("\n" + "=" * 50)
    print("🌤️  [1/4] 날씨 수집 테스트 (Open-Meteo)")
    print("=" * 50)
    try:
        from collectors.weather import collect_weather, collect_all_weather

        print("📍 경산 중방동 - 날씨 및 대기 정보 수집...")
        data = collect_weather("경산 중방동")
        if "error" in data:
            print(f"  ⚠️  Open-Meteo 오류: {data['error']}")
        else:
            print(
                f"  ✅ 현재 기온: {data.get('current_temp', 'N/A')}°C "
                f"(체감: {data.get('apparent_temp', 'N/A')}°C)"
            )
            print(f"  ✅ 미세먼지: {data.get('dust', 'N/A')}")
            print(
                f"  ✅ 풍속/습도: {data.get('wind_speed', 'N/A')} km/h, "
                f"{data.get('humidity', 'N/A')}%"
            )
            if data.get("forecast_3d"):
                for f in data["forecast_3d"]:
                    print(
                        f"  ✅ {f['date']}: {f['min']}~{f['max']}°C, 강수 {f['rain_prob']}"
                    )

        print("\n📍 전체 날씨 리포트 생성 테스트...")
        report = collect_all_weather()
        print(report)
        print("  → 날씨 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def test_stocks():
    print("\n" + "=" * 50)
    print("📈  [2/4] 주식 동향 수집 테스트 (yfinance + Google News RSS)")
    print("=" * 50)
    try:
        from collectors.stocks import collect_index_data, collect_stock_news

        print("📊 주요 지수 수집 중...")
        idx = collect_index_data()
        print(idx)

        time.sleep(1)

        print("📰 증권 뉴스 수집 (Google News RSS)...")
        news = collect_stock_news()
        lines = news.strip().splitlines()
        for line in lines[:8]:
            if line.strip():
                print(f"  {line}")
        print("  → 주식 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def test_it_news():
    print("\n" + "=" * 50)
    print("💻  [3/4] IT 뉴스 수집 테스트 (RSS + Hacker News)")
    print("=" * 50)
    try:
        from collectors.it_news import collect_rss_feeds, collect_hackernews

        print("📡 RSS 피드 수집 중...")
        articles = collect_rss_feeds()
        for a in articles[:5]:
            print(f"  [{a['source']}] {a['title'][:60]}...")

        time.sleep(1)

        print("\n📡 Hacker News 수집 중...")
        hn = collect_hackernews()
        for a in hn[:3]:
            print(f"  [HN] {a['title'][:60]}...")

        print(f"  → IT 뉴스 총 {len(articles) + len(hn)}건 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def test_civil_service():
    print("\n" + "=" * 50)
    print("🏛️  [4/4] 공무원 뉴스 수집 테스트 (Google News RSS)")
    print("=" * 50)
    try:
        from collectors.civil_service import search_civil_service_news

        for kw in ["공무원 정책", "전산직 공무원", "사회복지직"]:
            print(f"\n🔍 키워드: '{kw}' 검색...")
            articles = search_civil_service_news(kw, count=3)
            if not articles:
                print("    (기사 없음 또는 RSS 파싱 실패)")
            else:
                for a in articles:
                    print(f"  • {a['title'][:60]}...")
            time.sleep(0.5)

        print("\n  → 공무원 뉴스 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def print_env_status():
    """현재 로드된 주요 환경변수 설정 상태를 출력합니다."""
    gemini_ok = "✅ 설정됨" if Config.GEMINI_API_KEY else "❌ 미설정 (브리핑 실행 시 필수)"
    discord_ok = "✅ 설정됨" if Config.DISCORD_WEBHOOK_MAIN else "❌ 미설정 (브리핑 실행 시 필수)"

    print("⚙️  현재 환경변수 로드 상태:")
    print(f"  • Discord Webhook : {discord_ok}")
    print(f"  • Gemini API Key  : {gemini_ok}")
    print(f"    - 날씨 모델       : {Config.GEMINI_MODEL_WEATHER}")
    print(f"    - 주식 모델       : {Config.GEMINI_MODEL_STOCKS}")
    print(f"    - IT뉴스 모델     : {Config.GEMINI_MODEL_IT_NEWS}")
    print(f"    - 공무원뉴스 모델 : {Config.GEMINI_MODEL_CIVIL_SERVICE}")
    print(f"    - 폴백 모델       : {Config.GEMINI_MODEL_FALLBACK}")


if __name__ == "__main__":
    print("🚀 모닝브리핑 봇 - 수집기 테스트 시작")
    print("(모든 수집기는 별도 검색 API 키 없이 무료 RSS/오픈소스로 동작)")
    print("-" * 50)
    print_env_status()

    test_weather()
    test_stocks()
    test_it_news()
    test_civil_service()

    print("\n" + "=" * 50)
    print("✅ 수집기 테스트 완료!")
    print("=" * 50)
    print("\n다음 단계 및 .env 설정 안내:")
    print("  1. [필수] Discord 웹훅 URL:")
    print("     - DISCORD_WEBHOOK_MAIN=<디스코드_웹훅_URL>")
    print("     - (선택) DISCORD_WEBHOOK_WEATHER, DISCORD_WEBHOOK_STOCKS 등")
    print("  2. [필수] Google Gemini AI API 설정:")
    print("     - GEMINI_API_KEY=<구글_AI_스튜디오_API_키>")
    print("     - 카테고리별 모델 지정 (미지정 시 기본값 자동 적용):")
    print(f"       • GEMINI_MODEL_WEATHER={Config.GEMINI_MODEL_WEATHER} (기본: gemini-3.6-flash)")
    print(f"       • GEMINI_MODEL_STOCKS={Config.GEMINI_MODEL_STOCKS} (기본: gemini-3.6-flash)")
    print(f"       • GEMINI_MODEL_IT_NEWS={Config.GEMINI_MODEL_IT_NEWS} (기본: gemini-3.6-flash)")
    print(f"       • GEMINI_MODEL_CIVIL_SERVICE={Config.GEMINI_MODEL_CIVIL_SERVICE} (기본: gemini-3.6-flash)")
    print(f"       • GEMINI_MODEL_FALLBACK={Config.GEMINI_MODEL_FALLBACK} (기본: gemini-3.6-flash)")
    print("  3. [실행] 전체 모닝 브리핑 실행:")
    print("     - python main.py (또는 py main.py)")
