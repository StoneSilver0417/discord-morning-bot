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
            f"&hourly=temperature_2m,weather_code"
            f"&timezone=Asia/Seoul&forecast_days=1"
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

        hourly = result.get("hourly", {})
        if hourly:
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weather_code", [])
            
            active_hours = []
            for i in range(len(times)):
                # ISO 형식 시간에서 시간 추출 (예: 2026-05-13T08:00)
                hour_str = times[i].split("T")[-1].split(":")[0]
                hour = int(hour_str)
                if 8 <= hour <= 23:
                    # 기상 코드 단순화
                    cond = "맑음" if codes[i] <= 1 else "구름" if codes[i] <= 3 else "비/눈"
                    active_hours.append(f"{hour}시({temps[i]}°/{cond})")
            data["hourly_active"] = " | ".join(active_hours)

        logger.info(f"[Open-Meteo] {location_name} 보조 날씨 수집 완료")

    except Exception as e:
        logger.error(f"[Open-Meteo] {location_name} 수집 실패: {e}")
        data["error"] = str(e)

    return data


def collect_all_weather() -> str:
    """모든 지역의 날씨 정보를 수집하여 텍스트로 반환합니다."""
    from config import Config
    
    text = ""
    for loc in Config.WEATHER_LOCATIONS:
        n = collect_naver_weather(loc["query"])
        w = collect_wind_forecast(loc["name"])
        
        text += f"📍 **{loc['name']}**\n"
        
        if "error" not in n:
            curr = n.get('current_temp', 'N/A').replace("현재 온도", "").strip()
            text += f"🌡️ 현재: **{curr}** ({n.get('weather_desc', '-')})\n"
            
            # 미세먼지 정리
            dust_raw = n.get('dust', 'N/A')
            unique_dust = []
            seen = set()
            for d in [p.strip() for p in dust_raw.split(",")]:
                if d and d not in seen and ":" in d:
                    # '미세먼지: 좋음' -> '미세 좋음'
                    unique_dust.append(d.replace("미세먼지", "미세").replace("초미세먼지", "초미세"))
                    seen.add(d)
            if unique_dust:
                text += f"😷 대기: {', '.join(unique_dust[:2])}\n"
        
        if "error" not in w:
            # 08-23시 정보를 오전/오후/저녁으로 분리
            hourly_raw = w.get('hourly_active', '')
            if hourly_raw:
                parts = hourly_raw.split(" | ")
                morning = [p for p in parts if p.startswith(("8시", "9시", "10시", "11시"))]
                afternoon = [p for p in parts if p.startswith(("12시", "13시", "14시", "15시", "16시", "17시"))]
                evening = [p for p in parts if p.startswith(("18시", "19시", "20시", "21시", "22시", "23시"))]
                
                text += f"🌅 오전: {' '.join(morning)}\n"
                text += f"☀️ 오후: {' '.join(afternoon)}\n"
                text += f"🌙 저녁: {' '.join(evening)}\n"
            
            f3 = w.get("forecast_3d", [])
            if f3:
                today = f3[0]
                text += f"📊 예보: {today['min']}~{today['max']}°C (강수 {today['rain_prob']})\n"
        
        text += "\n"

    return text
