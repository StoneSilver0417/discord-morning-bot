import sys
from collectors.weather import collect_naver_weather

def test_dust_only():
    print("📍 경산 중방동 - 네이버 날씨 크롤링 (미세먼지 확인)...")
    data = collect_naver_weather("경산 중방동 날씨")
    if "error" in data:
        print(f"  ❌ 오류: {data['error']}")
    else:
        print(f"  ✅ 현재 기온: {data.get('current_temp', 'N/A')}")
        print(f"  ✅ 미세먼지 데이터: {data.get('dust', 'N/A')}")

if __name__ == "__main__":
    test_dust_only()
