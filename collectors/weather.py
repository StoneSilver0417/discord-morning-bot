"""날씨 수집기 - 네이버 날씨 + Windy 크롤링"""
import requests
from bs4 import BeautifulSoup
from config import Config
from utils.logger import setup_logger

logger = setup_logger("weather")


def collect_naver_weather(location_query: str) -> dict:
    """네이버 날씨 검색 결과를 크롤링합니다."""
    url = f"https://search.naver.com/search.naver?query={requests.utils.quote(location_query)}"
    data = {"location": location_query, "source": "naver"}

    try:
        resp = requests.get(url, headers=Config.HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 현재 온도
        temp_el = soup.select_one("div.temperature_text > strong")
        if temp_el:
            data["current_temp"] = temp_el.get_text(strip=True)

        # 체감 온도
        body_temp = soup.select_one("dd.desc")
        if body_temp:
            data["feels_like"] = body_temp.get_text(strip=True)

        # 날씨 상태 (맑음, 흐림 등)
        weather_summary = soup.select_one("span.weather.before_slash")
        if weather_summary:
            data["status"] = weather_summary.get_text(strip=True)

        # 최저/최고 온도
        min_max = soup.select("span.merge")
        if min_max:
            temps = [t.get_text(strip=True) for t in min_max]
            data["min_max"] = " / ".join(temps)

        # 미세먼지 (항목: 미세먼지, 초미세먼지, 자외선, 일몰 등)
        dust_items = soup.select("li.item_today")
        dust_info = []
        for item in dust_items:
            title = item.select_one(".title, span.label")
            value = item.select_one(".txt, span.txt")
            if title and value:
                t_text = title.get_text(strip=True)
                v_text = value.get_text(strip=True)
                # 필요한 항목만 필터링 (미세, 초미세, 자외선)
                if any(k in t_text for k in ["미세", "자외선"]):
                    dust_info.append(f"{t_text}: {v_text}")
        
        if not dust_info:
            # 보조: 다른 셀렉터 시도
            alt_dust = soup.select("ul.today_chart_list li")
            for item in alt_dust:
                text = item.get_text(separator=":", strip=True)
                if any(k in text for k in ["미세", "자외선"]):
                    dust_info.append(text)

        if dust_info:
            data["dust"] = ", ".join(dust_info)

        # 시간별 날씨
        hourly_items = soup.select("div.cell_weather")
        hourly = []
        for item in hourly_items[:8]:
            time_el = item.select_one("span.time")
            temp_el2 = item.select_one("span.temperature")
            if time_el and temp_el2:
                hourly.append(f"{time_el.get_text(strip=True)} {temp_el2.get_text(strip=True)}")
        if hourly:
            data["hourly"] = hourly

        # 강수확률
        rain_items = soup.select("span.rainfall")
        if rain_items:
            data["rain_probability"] = [r.get_text(strip=True) for r in rain_items[:8]]

        # 주간 날씨
        weekly_items = soup.select("div.weekly_item, div.item_day")
        weekly = []
        for item in weekly_items[:7]:
            text = item.get_text(separator=" ", strip=True)
            if text:
                weekly.append(text)
        if weekly:
            data["weekly"] = weekly

        logger.info(f"[네이버] {location_query} 날씨 수집 완료")

    except Exception as e:
        logger.error(f"[네이버] {location_query} 크롤링 실패: {e}")
        data["error"] = str(e)

    return data


def collect_wind_forecast(location_name: str) -> dict:
    """Open-Meteo API로 바람/기압/3일예보를 수집합니다.
    
    Windy.com은 JavaScript SPA라 직접 크롤링 불가.
    Open-Meteo는 Windy가 내부적으로 사용하는 동일한 기상모델(GFS/ECMWF)
    데이터를 무료로 제공하는 공개 API입니다.
    """
    data = {"location": location_name, "source": "windy"}

    # Windy는 SPA(Single Page Application)이라 직접 크롤링이 어려움
    # 대신 Open-Meteo API(무료)를 사용하여 바람/기압 데이터 보완
    coords = {
        "경산 중방동": {"lat": 35.8256, "lon": 128.7414},
        "대구 만촌동": {"lat": 35.8596, "lon": 128.6530},
    }

    coord = coords.get(location_name, coords["경산 중방동"])

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={coord['lat']}&longitude={coord['lon']}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,precipitation_probability_max,uv_index_max,"
            f"wind_speed_10m_max"
            f"&timezone=Asia/Seoul&forecast_days=3"
        )

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        result = resp.json()

        current = result.get("current", {})
        data["wind_speed"] = f"{current.get('wind_speed_10m', 'N/A')} km/h"
        data["wind_direction"] = f"{current.get('wind_direction_10m', 'N/A')}°"
        data["pressure"] = f"{current.get('surface_pressure', 'N/A')} hPa"
        data["humidity"] = f"{current.get('relative_humidity_2m', 'N/A')}%"
        data["precipitation"] = f"{current.get('precipitation', 0)} mm"

        daily = result.get("daily", {})
        if daily:
            forecast_3d = []
            dates = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            uv = daily.get("uv_index_max", [])
            for i in range(min(3, len(dates))):
                forecast_3d.append({
                    "date": dates[i] if i < len(dates) else "",
                    "max": maxs[i] if i < len(maxs) else "",
                    "min": mins[i] if i < len(mins) else "",
                    "rain_prob": f"{rain_probs[i]}%" if i < len(rain_probs) else "",
                    "uv": uv[i] if i < len(uv) else "",
                })
            data["forecast_3d"] = forecast_3d

        logger.info(f"[Open-Meteo] {location_name} 보조 날씨 수집 완료")

    except Exception as e:
        logger.error(f"[Open-Meteo] {location_name} 수집 실패: {e}")
        data["error"] = str(e)

    return data


def collect_all_weather() -> str:
    """모든 지역의 날씨 데이터를 수집하여 텍스트로 반환합니다."""
    all_data = []

    for loc in Config.WEATHER_LOCATIONS:
        naver = collect_naver_weather(loc["query"])
        wind = collect_wind_forecast(loc["name"])

        text = f"\n=== {loc['name']} ===\n"

        # 네이버 데이터
        text += f"[네이버 날씨]\n"
        text += f"현재 기온: {naver.get('current_temp', 'N/A')}\n"
        text += f"체감 온도: {naver.get('feels_like', 'N/A')}\n"
        text += f"날씨 상태: {naver.get('status', 'N/A')}\n"
        text += f"최저/최고: {naver.get('min_max', 'N/A')}\n"
        text += f"미세먼지: {naver.get('dust', 'N/A')}\n"

        if naver.get("rain_probability"):
            text += f"강수확률: {', '.join(naver['rain_probability'])}\n"
        if naver.get("hourly"):
            text += f"시간별: {' | '.join(naver['hourly'][:6])}\n"

        # GFS/ECMWF 기상모델 데이터 (Windy가 사용하는 것과 동일 소스)
        text += f"\n[바람/기압 정보 (기상모델 데이터)]\n"
        text += f"풍속: {wind.get('wind_speed', 'N/A')}\n"
        text += f"풍향: {wind.get('wind_direction', 'N/A')}\n"
        text += f"기압: {wind.get('pressure', 'N/A')}\n"
        text += f"습도: {wind.get('humidity', 'N/A')}\n"

        if wind.get("forecast_3d"):
            text += "\n[3일 예보]\n"
            for f in wind["forecast_3d"]:
                text += (
                    f"  {f['date']}: {f['min']}~{f['max']}°C, "
                    f"강수확률 {f['rain_prob']}, UV {f['uv']}\n"
                )

        if naver.get("weekly"):
            text += "\n[주간 날씨]\n"
            for w in naver["weekly"][:5]:
                text += f"  {w}\n"

        all_data.append(text)

    return "\n".join(all_data)
