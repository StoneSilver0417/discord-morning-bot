from datetime import datetime, timedelta, timezone


def get_kst_now():
    """대한민국 표준시(KST) 기준 현재 시간을 반환합니다."""
    # UTC+9
    return datetime.now(timezone(timedelta(hours=9)))


def get_kst_today_str():
    """KST 기준 오늘 날짜 문자열을 반환합니다. (예: 2026.05.14 (Thu))"""
    return get_kst_now().strftime("%Y.%m.%d (%a)")
