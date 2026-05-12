"""
수집기 단독 테스트 스크립트 (API 키 없이도 날씨/주식/뉴스 수집 확인 가능)

실행: py test_collectors.py
"""
import sys
import time

def test_weather():
    print("\n" + "="*50)
    print("🌤️  [1/4] 날씨 수집 테스트")
    print("="*50)
    try:
        from collectors.weather import collect_naver_weather, collect_wind_forecast
        
        print("📍 경산 중방동 - 네이버 날씨 크롤링...")
        data = collect_naver_weather("경산 중방동 날씨")
        if "error" in data:
            print(f"  ⚠️  네이버 오류: {data['error']}")
        else:
            print(f"  ✅ 현재 기온: {data.get('current_temp', 'N/A')}")
            print(f"  ✅ 날씨 상태: {data.get('status', 'N/A')}")
            print(f"  ✅ 최저/최고: {data.get('min_max', 'N/A')}")
            print(f"  ✅ 미세먼지: {data.get('dust', 'N/A')}")

        time.sleep(1)
        
        print("\n📍 경산 중방동 - 기상모델 데이터(Windy 동일 소스) 수집...")
        wind = collect_wind_forecast("경산 중방동")
        if "error" in wind:
            print(f"  ⚠️  Open-Meteo 오류: {wind['error']}")
        else:
            print(f"  ✅ 풍속: {wind.get('wind_speed', 'N/A')}")
            print(f"  ✅ 기압: {wind.get('pressure', 'N/A')}")
            print(f"  ✅ 습도: {wind.get('humidity', 'N/A')}")
            if wind.get("forecast_3d"):
                for f in wind["forecast_3d"]:
                    print(f"  ✅ {f['date']}: {f['min']}~{f['max']}°C, 강수 {f['rain_prob']}")

        print("\n📍 대구 만촌동 - 네이버 날씨 크롤링...")
        data2 = collect_naver_weather("대구 만촌동 날씨")
        if "error" in data2:
            print(f"  ⚠️  오류: {data2['error']}")
        else:
            print(f"  ✅ 현재 기온: {data2.get('current_temp', 'N/A')}")
            print(f"  ✅ 날씨 상태: {data2.get('status', 'N/A')}")

        print("  → 날씨 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def test_stocks():
    print("\n" + "="*50)
    print("📈  [2/4] 주식 동향 수집 테스트")
    print("="*50)
    try:
        from collectors.stocks import collect_index_data, collect_naver_finance_news
        
        print("📊 주요 지수 수집 중...")
        idx = collect_index_data()
        print(idx)

        time.sleep(1)

        print("📰 네이버 증권 뉴스 크롤링...")
        news = collect_naver_finance_news()
        lines = news.strip().splitlines()
        for line in lines[:8]:
            if line.strip():
                print(f"  {line}")
        print("  → 주식 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


def test_it_news():
    print("\n" + "="*50)
    print("💻  [3/4] IT 뉴스 수집 테스트")
    print("="*50)
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
    print("\n" + "="*50)
    print("🏛️  [4/4] 공무원 뉴스 수집 테스트")
    print("="*50)
    try:
        from collectors.civil_service import search_naver_news
        
        for kw in ["공무원 정책", "전산직 공무원", "사회복지직"]:
            print(f"\n🔍 키워드: '{kw}' 검색...")
            articles = search_naver_news(kw, count=3)
            for a in articles:
                print(f"  • {a['title'][:60]}...")
            time.sleep(0.5)
        
        print("  → 공무원 뉴스 수집 완료!")
    except Exception as e:
        print(f"  ❌ 실패: {e}")


if __name__ == "__main__":
    print("🚀 모닝브리핑 봇 - 수집기 테스트 시작")
    print("(API 키 없이도 수집기 동작 여부 확인)")
    
    test_weather()
    test_stocks()
    test_it_news()
    test_civil_service()
    
    print("\n" + "="*50)
    print("✅ 수집기 테스트 완료!")
    print("="*50)
    print("\n다음 단계:")
    print("  1. .env 파일에 DISCORD_WEBHOOK_MAIN 입력")
    print("  2. .env 파일에 GEMINI_API_KEY 입력")
    print("  3. py main.py 실행하여 전체 브리핑 테스트")
