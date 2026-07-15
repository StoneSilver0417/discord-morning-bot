"""Google Gemini LLM 요약/가공 프로세서"""
import google.generativeai as genai
from config import Config
from utils.logger import setup_logger

logger = setup_logger("gemini")

# Gemini 초기화
if Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)

# 카테고리별 시스템 프롬프트
SYSTEM_PROMPTS = {
    "weather": (
        "당신은 친근한 날씨 비서입니다. 부부가 함께 보는 메시지이므로 다정하고 실용적인 톤으로 작성하세요.\n"
        "다음 규칙을 따르세요:\n"
        "1. **활동 시간대(08시~23시)**의 기온 흐름과 날씨 변화를 중점적으로 요약하세요.\n"
        "2. 비/눈 소식이 있으면 가장 먼저 알려주세요.\n"
        "3. 오늘의 옷차림을 시간대별 기온에 맞춰 구체적으로 추천하세요.\n"
        "4. 우산, 미세먼지 등 외출 시 주의사항을 알려주세요.\n"
        "5. 두 지역(경산 중방동, 대구 만촌동) 정보를 비교하여 정리하세요."
    ),
    "stocks": (
        "당신은 주식 왕초보를 위한 친근한 시장 해설자입니다. 다음 규칙을 따르세요:\n"
        "1. 전체 시장 흐름을 '오늘 시장 분위기'로 3줄 요약.\n"
        "2. 어려운 금융 용어는 반드시 쉽게 풀어서 설명하세요.\n"
        "3. 오늘 주목할 뉴스 3개를 선별하여 왜 중요한지 이유와 함께 1줄씩 요약하세요.\n"
        "4. 마지막에 '오늘 요약 한 줄' 섹션으로 핵심만 정리하세요."
    ),
    "it_news": (
        "당신은 IT 트렌드 큐레이터입니다. 다음 규칙을 따르세요:\n"
        "1. **전산직 공무원(IT 인프라, 보안, 시스템 관리, 디지털 전환)**에게 실무적으로 도움될 내용을 우선 선별하세요.\n"
        "2. 국내외 공공기관, 정부 IT 정책, 보안 사고 예방 관련 기사는 반드시 포함하세요.\n"
        "3. 가장 중요한 뉴스 5개를 골라 아래 형식을 정확히 반복하세요.\n"
        "   번호. 기사 제목 (출처)\n"
        "   → 핵심 내용과 실무 의미를 쉬운 한국어 한 문장으로 요약\n"
        "   🔗 원문 URL\n"
        "4. 요약은 기사별 정확히 한 문장으로 쓰고, 원문에 없는 사실은 추측하지 마세요.\n"
        "5. 서론, 결론, 별도 총평 없이 뉴스 목록만 출력하세요."
    ),
    "civil_service": (
        "당신은 공무원 관련 뉴스 큐레이터입니다. 다음 규칙을 따르세요:\n"
        "1. [전산직] [복지직] [공통] 태그를 활용하여 중요한 뉴스 5~8개를 고르세요.\n"
        "2. 급여, 연금, 처우 개선, 채용 일정 등 모든 공무원에게 중요한 소식을 우선 포함하세요.\n"
        "3. 각 뉴스를 아래 형식으로 정확히 반복하세요.\n"
        "   번호. [직렬 태그] 기사 제목\n"
        "   → 핵심 내용과 공무원에게 미치는 영향을 쉬운 한국어 한 문장으로 요약\n"
        "   🔗 원문 URL\n"
        "4. 요약은 기사별 정확히 한 문장으로 쓰고, 원문에 없는 사실은 추측하지 마세요.\n"
        "5. 서론, 결론, 별도 총평 없이 뉴스 목록만 출력하세요."
    ),
    "briefing_summary": (
        "다음 4개 카테고리(날씨, 주식, IT뉴스, 공무원) 정보를 각 1~2줄로 초간단 요약해서\n"
        "종합 모닝 브리핑을 만들어주세요. 부부가 함께 보는 메시지이므로 다정한 톤으로,\n"
        "마지막에 '좋은 하루 보내세요! 💕' 같은 인사를 넣어주세요."
    ),
}


def _is_quota_exhausted(error: Exception) -> bool:
    """Gemini 할당량 소진(HTTP 429/RESOURCE_EXHAUSTED) 오류인지 확인합니다."""
    error_text = f"{type(error).__name__} {error}".lower()
    quota_markers = (
        "resourceexhausted",
        "resource_exhausted",
        "quota exceeded",
        "quota_exceeded",
        "429",
    )
    return any(marker in error_text for marker in quota_markers)


def process_with_gemini(category: str, raw_data: str) -> str:
    """Gemini를 사용하여 원시 데이터를 가공합니다."""
    if not raw_data or not raw_data.strip():
        raise ValueError(f"[{category}] Gemini에 전달할 수집 데이터가 비어 있습니다.")
    if not Config.GEMINI_API_KEY:
        logger.warning("Gemini API 키 미설정 - 원본 데이터 반환")
        return raw_data

    system_prompt = SYSTEM_PROMPTS.get(category, "다음 내용을 한국어로 간결하게 요약해주세요.")

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content(
            f"{system_prompt}\n\n--- 데이터 ---\n{raw_data}",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1500,
                temperature=0.7,
            ),
        )
        result = response.text.strip()
        if not result:
            raise RuntimeError("Gemini 응답이 비어 있습니다.")
        logger.info(f"[{category}] Gemini 가공 완료 ({len(result)}자)")
        return result

    except Exception as e:
        logger.error(f"[{category}] Gemini 에러: {e}")
        if _is_quota_exhausted(e):
            logger.warning(
                f"[{category}] Gemini 할당량 소진 - 수집한 원문 전체를 전송합니다."
            )
            return raw_data
        raise RuntimeError(f"[{category}] Gemini 가공 실패") from e


def add_windy_links(text: str) -> str:
    """텍스트 끝에 Windy 바로가기 링크를 추가합니다."""
    links = (
        "\n\n🌐 **Windy 바로가기**\n"
        "• [경산 중방동](https://www.windy.com/35.826/128.741)\n"
        "• [대구 만촌동](https://www.windy.com/35.860/128.653)"
    )
    return text + links
