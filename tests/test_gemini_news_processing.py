from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from processors.gemini_processor import process_with_gemini


def _raw_news(count: int) -> str:
    blocks = [
        (
            f"{index}. **기사 {index}** (테스트)\n"
            f"설명: 기사 {index} 핵심 설명\n"
            f"🔗 https://example.com/news/{index}"
        )
        for index in range(1, count + 1)
    ]
    return f"[뉴스 수집 결과 - 총 {count}건]\n\n" + "\n\n".join(blocks)


def _ranked_news(indices: list[int]) -> str:
    return "\n\n".join(
        (
            f"{position}. [상] 기사 {index}\n"
            f"• 내용 요약: 기사 {index}의 핵심 내용\n"
            "• 실무/영향: 업무에 미치는 영향\n"
            f"🔗 https://example.com/news/{index}"
        )
        for position, index in enumerate(indices, 1)
    )


@pytest.mark.parametrize("category", ["it_news", "civil_service"])
@patch("processors.gemini_processor.genai.Client")
def test_news_accepts_ten_ranked_stories_from_full_candidate_pool(
    mocked_client: Mock,
    category: str,
) -> None:
    # Given
    raw_news = _raw_news(12)
    ranked_news = _ranked_news([12, 11, 10, 9, 8, 7, 6, 5, 4, 3])
    response = Mock(
        text=ranked_news,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
    )
    mocked_client.return_value.models.generate_content.return_value = response

    # When
    with patch("processors.gemini_processor.Config.GEMINI_API_KEY", "test-key"):
        result = process_with_gemini(category, raw_news)

    # Then
    assert result == ranked_news
    assert result.count("🔗 http") == 10
    assert "https://example.com/news/12" in result
    prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
    assert "https://example.com/news/12" in prompt


@patch("processors.gemini_processor.genai.Client")
def test_incomplete_ranking_falls_back_to_exactly_ten_stories(
    mocked_client: Mock,
) -> None:
    # Given
    raw_news = _raw_news(12)
    response = Mock(
        text=_ranked_news(list(range(9, 0, -1))),
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
    )
    mocked_client.return_value.models.generate_content.return_value = response

    # When
    with patch("processors.gemini_processor.Config.GEMINI_API_KEY", "test-key"):
        result = process_with_gemini("it_news", raw_news)

    # Then
    assert result.count("🔗 http") == 10
    assert "https://example.com/news/10" in result
    assert "https://example.com/news/11" not in result


def test_missing_api_key_falls_back_to_exactly_ten_stories() -> None:
    # Given
    raw_news = _raw_news(12)

    # When
    with patch("processors.gemini_processor.Config.GEMINI_API_KEY", ""):
        result = process_with_gemini("civil_service", raw_news)

    # Then
    assert result.count("🔗 http") == 10
    assert "https://example.com/news/11" not in result


@patch("processors.gemini_processor.genai.Client")
def test_it_news_translates_english_articles_into_korean(
    mocked_client: Mock,
) -> None:
    # Given
    english_raw = (
        "[IT 뉴스 수집 결과 - 총 2건]\n\n"
        "1. **Apple announces new M4 MacBook Pro lineup** (TechCrunch)\n"
        "설명: Apple has revealed its latest MacBook Pro models powered by M4 chips.\n"
        "🔗 https://example.com/apple-m4\n\n"
        "2. **OpenAI launches search features for ChatGPT** (Wired)\n"
        "설명: OpenAI brings real-time web search capabilities directly to ChatGPT.\n"
        "🔗 https://example.com/openai-search"
    )
    translated_ranked = (
        "1. [상] [하드웨어] 애플, M4 칩 탑재 신형 맥북 프로 라인업 발표 (TechCrunch)\n"
        "• 내용 요약: 애플이 차세대 M4 칩을 탑재한 맥북 프로 라인업을 공개했습니다.\n"
        "• 실무/영향: 고성능 업무 환경 구축 시 최신 사양 검토가 필요합니다.\n"
        "🔗 https://example.com/apple-m4\n\n"
        "2. [중] [AI] 오픈AI, 챗GPT 실시간 검색 기능 출시 (Wired)\n"
        "• 내용 요약: 챗GPT에서 최신 웹 정보를 직접 검색할 수 있게 되었습니다.\n"
        "• 실무/영향: 업무 리서치 및 정보 수집 효율이 크게 향상될 것으로 기대됩니다.\n"
        "🔗 https://example.com/openai-search"
    )
    response = Mock(
        text=translated_ranked,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
    )
    mocked_client.return_value.models.generate_content.return_value = response

    # When
    with patch("processors.gemini_processor.Config.GEMINI_API_KEY", "test-key"):
        result = process_with_gemini("it_news", english_raw)

    # Then
    assert result == translated_ranked
    prompt = mocked_client.return_value.models.generate_content.call_args.kwargs["contents"]
    assert "한국어로 번역" in prompt
