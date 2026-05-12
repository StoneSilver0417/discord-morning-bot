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
        "1. 비/눈 소식이 있으면 가장 먼저 알려주세요\n"
        "2. 오늘의 옷차림을 구체적으로 추천하세요\n"
        "3. 우산, 미세먼지 등 외출 시 주의사항을 알려주세요\n"
        "4. 이모지를 적절히 활용하세요\n"
        "5. 두 지역(경산 중방동, 대구 만촌동) 정보를 함께 정리하세요"
    ),
    "stocks": (
        "당신은 주식 왕초보를 위한 친근한 시장 해설자입니다. 다음 규칙을 따르세요:\n"
        "1. 전체 시장 흐름을 '오늘 시장 분위기'로 3줄 요약. 예: '오늘은 전반적으로 하락세였어요. 미국 금리 불안 소식 때문인데...'\n"
        "2. 어려운 금융 용어는 반드시 쉽게 풀어서 설명하세요. 예: '하락장(-2%)' → '어제보다 주가가 2% 떨어졌어요'\n"
        "3. 오늘 주목할 뉴스 3개를 1줄씩 요약 (왜 중요한지 이유 포함)\n"
        "4. 마지막에 '오늘 요약 한 줄' 섹션으로 핵심만 한 문장으로 정리\n"
        "5. 투자 권유나 판단은 절대 하지 말고, 객관적 사실만 전달\n"
        "6. 이모지를 적절히 활용하세요"
    ),
    "it_news": (
        "당신은 IT 트렌드 큐레이터입니다. 다음 규칙을 따르세요:\n"
        "1. 전산직 공무원(IT 인프라/보안/시스템 관리)에게 유용한 기사 우선 선별\n"
        "2. 공공기관/정부 IT 관련 기사가 있으면 반드시 포함\n"
        "3. 5~7개 기사를 선별하여 각 2줄로 한국어 요약\n"
        "4. 기술 트렌드, 보안 이슈, 클라우드/인프라 관련 내용 우선\n"
        "5. 원문 링크를 포함하세요"
    ),
    "civil_service": (
        "당신은 공무원 관련 뉴스 큐레이터입니다. 다음 규칙을 따르세요:\n"
        "1. [전산직] 태그: 전산/IT/정보보안/디지털 관련 내용\n"
        "2. [복지직] 태그: 사회복지/복지정책/복지서비스 관련 내용\n"
        "3. [공통] 태그: 급여/수당/복지/인사/시험/채용 등 모든 공무원 해당 뉴스\n"
        "4. 전산직과 사회복지직에 해당하지 않더라도 공무원 전반에 중요한 뉴스는 반드시 포함\n"
        "5. 5~8개 뉴스를 선별하여 각 2줄로 요약\n"
        "6. 중요한 내용은 ⭐, 시험/채용 관련은 📋, 처우/급여 관련은 💰으로 표시"
    ),
    "briefing_summary": (
        "다음 4개 카테고리(날씨, 주식, IT뉴스, 공무원) 정보를 각 1~2줄로 초간단 요약해서\n"
        "종합 모닝 브리핑을 만들어주세요. 부부가 함께 보는 메시지이므로 다정한 톤으로,\n"
        "마지막에 '좋은 하루 보내세요! 💕' 같은 인사를 넣어주세요."
    ),
}


def process_with_gemini(category: str, raw_data: str) -> str:
    """Gemini를 사용하여 원시 데이터를 가공합니다."""
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
        logger.info(f"[{category}] Gemini 가공 완료 ({len(result)}자)")
        return result

    except Exception as e:
        logger.error(f"[{category}] Gemini 에러: {e}")
        return f"(LLM 요약 실패 - 원본 요약)\n{raw_data[:1000]}"


def add_windy_links(text: str) -> str:
    """텍스트 끝에 Windy 바로가기 링크를 추가합니다."""
    links = (
        "\n\n🌐 **Windy 바로가기**\n"
        "• [경산 중방동](https://www.windy.com/35.826/128.741)\n"
        "• [대구 만촌동](https://www.windy.com/35.860/128.653)"
    )
    return text + links
