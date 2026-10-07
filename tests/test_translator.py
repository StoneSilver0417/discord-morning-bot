"""Tests for translation and localization utilities."""
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from utils.translator import (
    _TRANSLATION_CACHE,
    is_primarily_english,
    localize_news_body,
    translate_article_summary,
    translate_article_title,
    translate_en_to_ko,
)
from processors.news_selection import build_news_contract
from collectors.it_news import collect_all_it_news


def test_is_primarily_english_detection() -> None:
    assert is_primarily_english("Apple announces new M4 MacBook Pro")
    assert is_primarily_english("OpenAI launches ChatGPT search")
    assert not is_primarily_english("애플, 신형 맥북 프로 공개")
    assert not is_primarily_english("네이버 AI 검색 서비스 발표")
    assert not is_primarily_english("공무원 처우 개선 2026")
    assert not is_primarily_english("")
    assert not is_primarily_english(None)
    assert not is_primarily_english("1234567890 !@#$%")


def test_translate_en_to_ko_success() -> None:
    _TRANSLATION_CACHE.clear()
    fake_response_data = json.dumps({
        "responseData": {
            "translatedText": "애플, 새로운 M4 맥북 프로 라인업 발표",
            "match": 1,
        }
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_response_data
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = translate_en_to_ko("Apple announces new M4 MacBook Pro lineup")

    assert result == "애플, 새로운 M4 맥북 프로 라인업 발표"


def test_translate_en_to_ko_returns_none_on_network_error() -> None:
    _TRANSLATION_CACHE.clear()
    with patch("urllib.request.urlopen", side_effect=Exception("Network down")):
        result = translate_en_to_ko("Some English Article Title")

    assert result is None


def test_translate_en_to_ko_skips_korean() -> None:
    assert translate_en_to_ko("이미 한국어인 텍스트") == "이미 한국어인 텍스트"


def test_translate_article_title_translates_or_falls_back() -> None:
    _TRANSLATION_CACHE.clear()
    with patch("utils.translator.translate_en_to_ko", return_value="애플 신제품 출시"):
        assert translate_article_title("Apple releases new product") == "애플 신제품 출시"

    with patch("utils.translator.translate_en_to_ko", return_value=None):
        assert translate_article_title("Apple releases new product") == "Apple releases new product"

    assert translate_article_title("한국어 기사 제목") == "한국어 기사 제목"


def test_translate_article_summary_translates_or_falls_back() -> None:
    _TRANSLATION_CACHE.clear()
    with patch("utils.translator.translate_en_to_ko", return_value="새로운 기능이 출시되었습니다."):
        assert (
            translate_article_summary("The new feature has been released.")
            == "새로운 기능이 출시되었습니다."
        )

    with patch("utils.translator.translate_en_to_ko", return_value=None):
        fallback = translate_article_summary("The new feature has been released.")
        assert "해외 IT 기사 원문입니다." in fallback

    assert translate_article_summary("이미 작성된 한국어 요약") == "이미 작성된 한국어 요약"
    assert translate_article_summary("") == "기사 설명 없음"


def test_localize_news_body_translates_markdown_candidate() -> None:
    _TRANSLATION_CACHE.clear()
    english_body = (
        "**Apple announces new M4 MacBook Pro lineup** (TechCrunch)\n"
        "설명: Apple has revealed its latest MacBook Pro models powered by M4 chips.\n"
        "🔗 https://example.com/apple-m4"
    )

    with patch("utils.translator.translate_article_title", return_value="애플, 신형 M4 맥북 발표"):
        with patch("utils.translator.translate_article_summary", return_value="애플이 M4 맥북을 공개했습니다."):
            localized = localize_news_body(english_body)

    assert "**애플, 신형 M4 맥북 발표** (TechCrunch)" in localized
    assert "설명: 애플이 M4 맥북을 공개했습니다." in localized
    assert "🔗 https://example.com/apple-m4" in localized


def test_build_news_contract_fallback_localizes_english_candidates() -> None:
    _TRANSLATION_CACHE.clear()
    raw_news = (
        "[IT 뉴스 수집 결과 - 총 1건]\n\n"
        "1. **FTC opens investigation** (The Verge)\n"
        "설명: The FTC is examining tech giants.\n"
        "🔗 https://example.com/ftc"
    )

    with patch("utils.translator.translate_article_title", return_value="FTC, 빅테크 조사 개시"):
        with patch("utils.translator.translate_article_summary", return_value="FTC가 대형 기술기업을 조사합니다."):
            contract = build_news_contract(raw_news)

    assert "FTC, 빅테크 조사 개시" in contract.fallback_text
    assert "FTC가 대형 기술기업을 조사합니다." in contract.fallback_text
    assert "https://example.com/ftc" in contract.fallback_text


def test_collect_all_it_news_translates_foreign_articles() -> None:
    _TRANSLATION_CACHE.clear()
    now = None
    from datetime import datetime, timezone
    now = datetime(2026, 10, 7, 7, 0, tzinfo=timezone.utc)

    mock_article = {
        "source": "TechCrunch",
        "title": "OpenAI releases new reasoning model",
        "link": "https://example.com/openai",
        "summary": "OpenAI has officially launched its newest AI reasoning model.",
        "published_at": now,
    }

    with (
        patch("collectors.it_news.collect_rss_feeds", return_value=[mock_article]),
        patch("collectors.it_news.collect_hackernews", return_value=[]),
        patch("collectors.it_news._get_now", return_value=now),
        patch("collectors.it_news.translate_article_title", return_value="오픈AI, 신규 추론 모델 출시"),
        patch("collectors.it_news.translate_article_summary", return_value="오픈AI가 새로운 AI 추론 모델을 공식 출시했습니다."),
        patch("collectors.it_news.filter_fresh", side_effect=lambda articles, store, cat, now, max_age_hours: articles),
    ):
        result = collect_all_it_news()

    assert "오픈AI, 신규 추론 모델 출시" in result
    assert "오픈AI가 새로운 AI 추론 모델을 공식 출시했습니다." in result
    assert "https://example.com/openai" in result


def test_workflow_cron_schedule_configuration() -> None:
    workflow_path = Path(".github") / "workflows" / "morning_briefing.yml"
    assert workflow_path.exists()
    content = workflow_path.read_text(encoding="utf-8")
    assert "50 21 * * *" in content
    assert "21:50" in content
