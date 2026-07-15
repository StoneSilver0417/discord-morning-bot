"""Discord Webhook 메시지 포맷터 및 전송"""
import requests
from utils.logger import setup_logger

logger = setup_logger("formatter")

# 카테고리별 색상 (Discord Embed color는 정수)
COLORS = {
    "weather": 0x3498DB,      # 파란색
    "stocks": 0x2ECC71,       # 초록색
    "it_news": 0x9B59B6,      # 보라색
    "civil_service": 0xF39C12, # 주황색
    "briefing": 0xE74C3C,     # 빨간색 (종합)
}

EMOJI = {
    "weather": "🌤️",
    "stocks": "📈",
    "it_news": "💻",
    "civil_service": "🏛️",
    "briefing": "☀️",
}


def create_embed(category: str, title: str, description: str, fields: list = None) -> dict:
    """Discord Embed 객체를 생성합니다."""
    embed = {
        "title": f"{EMOJI.get(category, '📋')} {title}",
        "description": description[:4096] if description else "",
        "color": COLORS.get(category, 0x95A5A6),
    }
    if fields:
        embed["fields"] = []
        for field in fields[:25]:  # Discord 최대 25 필드
            embed["fields"].append({
                "name": str(field.get("name", ""))[:256],
                "value": str(field.get("value", ""))[:1024],
                "inline": field.get("inline", False),
            })
    return embed


def create_embeds(category: str, title: str, description: str) -> list:
    """긴 설명을 Discord embed 제한에 맞춰 내용 손실 없이 나눕니다."""
    if not description:
        return [create_embed(category, title, "")]

    chunks = []
    remaining = description
    while remaining:
        if len(remaining) <= 4096:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, 4097)
        if split_at <= 0:
            split_at = 4096
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]

    total = len(chunks)
    return [
        create_embed(
            category,
            title if total == 1 else f"{title} ({index}/{total})",
            chunk,
        )
        for index, chunk in enumerate(chunks, 1)
    ]


def send_webhook(webhook_url: str, content: str = None, embeds: list = None, username: str = "모닝브리핑 봇") -> bool:
    """Discord Webhook으로 메시지를 전송합니다."""
    if not webhook_url:
        logger.error("Webhook URL이 설정되지 않았습니다.")
        return False

    payload = {"username": username}
    if content:
        payload["content"] = content[:2000]
    if embeds:
        # Discord는 한 번에 최대 10개 embed
        payload["embeds"] = embeds[:10]

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            logger.info("메시지 전송 성공")
            return True
        else:
            logger.error(f"메시지 전송 실패: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Webhook 전송 에러: {e}")
        return False


def send_multiple_embeds(webhook_url: str, embeds: list, username: str = "모닝브리핑 봇") -> bool:
    """Discord의 메시지당 embed 전체 텍스트 제한을 피해 하나씩 전송합니다."""
    success = True
    for embed in embeds:
        if not send_webhook(webhook_url, embeds=[embed], username=username):
            success = False
    return success
