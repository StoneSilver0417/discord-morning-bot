"""날씨 수집기 - Open-Meteo Forecast & Air Quality API 통합"""
import requests
from config import Config
from utils.logger import setup_logger
from utils.time_utils import get_kst_now

logger = setup_logger("weather")

COORDINATES = {
    "경산 중방동": {"lat": 35.8256, "lon": 128.7414},
    "대구 만촌동": {"lat": 35.8596, "lon": 128.6530},
}


def get_pm10_grade(val: float | int | None) -> str:
    """한국 환경부 기준 미세먼지(PM10) 등급을 반환합니다."""
    if val is None:
        return "정보없음"
    if val <= 30:
        return "좋음"
    if val <= 80:
        return "보통"
    if val <= 150:
        return "나쁨"
    return "매우나쁨"


def get_pm25_grade(val: float | int | None) -> str:
    """한국 환경부 기준 초미세먼지(PM2.5) 등급을 반환합니다."""
    if val is None:
        return "정보없음"
    if val <= 15:
        return "좋음"
    if val <= 35:
        return "보통"
    if val <= 75:
        return "나쁨"
    return "매우나쁨"


def get_weather_condition(code: int) -> str:
    """WMO 기상 코드를 한국어 날씨 상태로 변환합니다."""
    if code <= 1:
        return "맑음"
    if code <= 3:
        return "구름"
    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "비"
    if code in {71, 73, 75, 77, 85, 86}:
        return "눈"
    if code in {95, 96, 99}:
        return "뇌우"
    return "비/눈"


def _fetch_open_meteo(url: str, timeout: int = 10, retries: int = 2) -> requests.Response:
    """Open-Meteo API 호출을 수행하며 일시 오류 시 재시도합니다."""
    import time
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1)
    if last_err:
        raise last_err
    raise RuntimeError(f"Open-Meteo 호출 실패: {url}")


def collect_air_quality(lat: float, lon: float) -> dict:
    """Open-Meteo Air Quality API로 미세먼지(PM10) 및 초미세먼지(PM2.5)를 수집합니다."""
    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}&current=pm10,pm2_5&timezone=Asia/Seoul"
    )
    resp = _fetch_open_meteo(url, timeout=10)
    result = resp.json()
    current = result.get("current", {})

    pm10 = current.get("pm10")
    pm2_5 = current.get("pm2_5")

    pm10_grade = get_pm10_grade(pm10)
    pm25_grade = get_pm25_grade(pm2_5)

    dust_parts = []
    if pm10 is not None:
        dust_parts.append(f"미세: {round(pm10)}㎍/㎥ ({pm10_grade})")
    if pm2_5 is not None:
        dust_parts.append(f"초미세: {round(pm2_5)}㎍/㎥ ({pm25_grade})")

    dust_str = ", ".join(dust_parts) if dust_parts else "미세먼지 정보 없음"

    return {
        "pm10": pm10,
        "pm10_grade": pm10_grade,
        "pm2_5": pm2_5,
        "pm2_5_grade": pm25_grade,
        "dust": dust_str,
    }


def collect_weather(location_name: str) -> dict:
    """Open-Meteo API를 사용하여 특정 지역의 종합 날씨 정보를 수집합니다."""
    data = {"location": location_name, "source": "open-meteo"}
    coord = COORDINATES.get(location_name, COORDINATES["경산 중방동"])
    today_str = get_kst_now().strftime("%Y-%m-%d")

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
            f"&timezone=Asia/Seoul"
            f"&start_date={today_str}&end_date={today_str}"
        )

        resp = _fetch_open_meteo(url, timeout=10)
        result = resp.json()

        daily = result.get("daily", {})
        dates = daily.get("time", []) if daily else []
        if not dates or dates[0] != today_str:
            raise ValueError(
                f"Open-Meteo 예보 날짜 불일치: 요청={today_str}, 응답={dates[:1]}"
            )

        current = result.get("current", {})
        data["current_temp"] = current.get("temperature_2m")
        data["apparent_temp"] = current.get("apparent_temperature")
        data["humidity"] = current.get("relative_humidity_2m")
        data["precipitation"] = current.get("precipitation", 0.0)
        data["wind_speed"] = current.get("wind_speed_10m")
        data["wind_direction"] = current.get("wind_direction_10m")
        data["pressure"] = current.get("surface_pressure")
        data["weather_code"] = current.get("weather_code")

        maxs = daily.get("temperature_2m_max", [])
        mins = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        uv = daily.get("uv_index_max", [])

        forecast_3d = []
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
                hour_str = times[i].split("T")[-1].split(":")[0]
                hour = int(hour_str)
                if 8 <= hour <= 23:
                    cond = get_weather_condition(codes[i])
                    active_hours.append(f"{hour}시({temps[i]}°/{cond})")
            data["hourly_active"] = " | ".join(active_hours)

        # 미세먼지 수집
        try:
            air = collect_air_quality(coord["lat"], coord["lon"])
            data.update(air)
        except Exception as air_err:
            logger.warning(f"[Open-Meteo] {location_name} 미세먼지 수집 실패: {air_err}")
            data["dust"] = "미세먼지 정보 없음"

        logger.info(f"[Open-Meteo] {location_name} 날씨 및 대기 정보 수집 완료")

    except Exception as e:
        logger.error(f"[Open-Meteo] {location_name} 수집 실패: {e}")
        data["error"] = str(e)

    return data


# 기존 테스트 및 코드 호환성을 위한 별칭
collect_wind_forecast = collect_weather


def calculate_period_stats(parts: list[str], target_hours: list[str]) -> dict | None:
    """시간대별 예보 목록에서 지정된 시간대의 평균 기온 및 대표 날씨 상태를 계산합니다."""
    items = [p for p in parts if p.split("시")[0] in target_hours]
    if not items:
        return None
    temps = [float(p.split("(")[1].split("°")[0]) for p in items]
    conds = [p.split("/")[1].replace(")", "") for p in items]
    avg_temp = sum(temps) / len(temps)
    main_cond = max(set(conds), key=conds.count)
    return {"avg": round(avg_temp, 1), "cond": main_cond}


def collect_all_weather() -> str:
    """모든 지역의 날씨 정보를 수집하여 텍스트형 리포트로 반환합니다."""
    text = ""
    locations = [loc["name"] for loc in Config.WEATHER_LOCATIONS] if hasattr(Config, "WEATHER_LOCATIONS") else list(COORDINATES.keys())

    for loc_name in locations:
        w = collect_weather(loc_name)

        if "error" in w or not w.get("forecast_3d"):
            raise RuntimeError(
                f"{loc_name} 오늘 예보 수집 실패: {w.get('error', '오늘 예보 없음')}"
            )

        text += f"📍 **{loc_name} 날씨 리포트**\n"

        # 1. 최고/최저 및 현재 기온, 체감온도
        f3 = w.get("forecast_3d", [])
        today = f3[0]
        cur_temp = w.get("current_temp", "N/A")
        app_temp = w.get("apparent_temp")
        temp_line = f"🌡️ **기온**: {today['min']}° ~ {today['max']}° (현재 {cur_temp}°"
        if app_temp is not None:
            temp_line += f", 체감 {app_temp}°"
        temp_line += ")\n"
        text += temp_line

        # 2. 미세먼지
        dust_info = w.get("dust")
        if dust_info:
            text += f"😷 **대기**: {dust_info}\n"

        # 3. 추가 기상 상세 (습도, 풍속, 강수확률, 자외선)
        details = []
        if w.get("humidity") is not None:
            details.append(f"습도 {w['humidity']}%")
        if w.get("wind_speed") is not None:
            details.append(f"풍속 {w['wind_speed']}km/h")
        rain_prob = today.get("rain_prob")
        if rain_prob:
            details.append(f"강수확률 {rain_prob}")
        uv = today.get("uv")
        if uv:
            details.append(f"자외선 {uv}")
        if details:
            text += f"💧 **상세**: {', '.join(details)}\n"

        # 4. 시간대별 요약 계산 (오전/오후/저녁)
        hourly_raw = w.get("hourly_active", "")
        if hourly_raw:
            parts = hourly_raw.split(" | ")
            morning = calculate_period_stats(parts, ["8", "9", "10", "11"])
            afternoon = calculate_period_stats(parts, ["12", "13", "14", "15", "16", "17"])
            evening = calculate_period_stats(parts, ["18", "19", "20", "21", "22", "23"])

            text += "📊 **시간대별 요약**\n"
            if morning:
                text += f"└ 🌅 오전: 평균 **{morning['avg']}°** ({morning['cond']})\n"
            if afternoon:
                text += f"└ ☀️ 오후: 평균 **{afternoon['avg']}°** ({afternoon['cond']})\n"
            if evening:
                text += f"└ 🌙 저녁: 평균 **{evening['avg']}°** ({evening['cond']})\n"

        text += "\n"

    return text
