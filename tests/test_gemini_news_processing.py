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
