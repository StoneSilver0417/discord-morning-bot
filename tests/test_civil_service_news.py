from datetime import datetime, timedelta, timezone
from typing import TypedDict
from unittest.mock import MagicMock, patch

from collectors.civil_service import (
    _articles_are_duplicates,
    _is_relevant,
    collect_all_civil_service,
    search_civil_service_news,
)


class ArticleFixture(TypedDict):
    title: str
    summary: str
    link: str
    pubDate: str
    published_at: datetime


def _article(
    title: str,
    summary: str,
    link: str,
    published_at: datetime,
) -> ArticleFixture:
    return {
        "title": title,
        "summary": summary,
        "link": link,
        "pubDate": published_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "published_at": published_at,
    }


def test_duplicate_detection_handles_rewording_but_preserves_numeric_variants() -> None:
    base = {
        "title": "공무원연금 2년 공백, 법원 판단은 - 다음뉴스",
        "summary": "퇴직 공무원의 연금 지급 개시 시점에 관한 판결",
    }
    reworded = {
        "title": "공무원연금 2년 공백…법원의 판단은 - 중앙일보",
        "summary": "퇴직 공무원의 연금 지급 시기를 다룬 법원 판결",
    }
    different_grade = {
        "title": "9급 공무원 채용 일정 발표",
        "summary": "9급 국가직 공무원 채용 일정",
    }
    seventh_grade = {
        "title": "7급 공무원 채용 일정 발표",
        "summary": "7급 국가직 공무원 채용 일정",
    }

    assert _articles_are_duplicates(base, reworded)
    assert not _articles_are_duplicates(different_grade, seventh_grade)

    numbered = {
        "title": "공무원 보수 3% 인상 확정",
        "summary": "정부가 공무원 보수 인상안을 확정했다",
    }
    number_omitted = {
        "title": "공무원 보수 인상 확정",
        "summary": "정부가 공무원 보수 인상안을 확정했다",
    }
    assert _articles_are_duplicates(numbered, number_omitted)

    seoul = {
        "title": "서울시 지방직 공무원 채용 일정 발표",
        "summary": "서울시가 올해 지방직 선발 일정을 공개했다",
    }
    busan = {
        "title": "부산시 지방직 공무원 채용 일정 발표",
        "summary": "부산시가 하반기 지방직 시험 계획을 안내했다",
    }
    assert not _articles_are_duplicates(seoul, busan)


def test_relevance_filter_rejects_misleading_public_official_term() -> None:
    article = {
        "title": "고위공직자범죄수사처 수사 결과 발표",
        "summary": "수사기관이 사건 처리 결과를 공개했다",
    }

    assert not _is_relevant(article)


def test_relevance_filter_rejects_foreign_civil_service_news() -> None:
    foreign_articles = [
        {
            "title": "베트남 공무원 임금 개혁 추진",
            "summary": "베트남 정부가 공무원 급여 체계를 개편한다",
        },
        {
            "title": "미 연방 공무원 감축 계획 발표",
            "summary": "미국 정부의 공공부문 인력 정책",
        },
        {
            "title": "오스트리아와 스위스의 공무원연금 개혁",
            "summary": "유럽 각국의 연금 제도를 비교한다",
        },
        {
            "title": "유엔, 태평양 도서국 공무원 초청 연수",
            "summary": "국제기구가 해외 공무원을 대상으로 연수를 열었다",
        },
    ]

    results = [_is_relevant(article) for article in foreign_articles]

    assert results == [False, False, False, False]


@patch("collectors.civil_service.feedparser.parse")
def test_search_query_limits_results_to_korean_public_administration(
    mock_parse: MagicMock,
) -> None:
    mock_parse.return_value.bozo = False
    mock_parse.return_value.entries = [
        {
            "title": "베트남 공무원 임금 개혁 추진",
            "summary": "베트남 정부가 공무원 급여 체계를 개편한다",
            "link": "https://example.com/vietnam",
            "published": "Wed, 02 Sep 2026 09:00:00 GMT",
        }
    ]

    articles = search_civil_service_news("공무원 정책")

    query_url = mock_parse.call_args.args[0]
    assert "%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD" in query_url
    assert "-%EB%B2%A0%ED%8A%B8%EB%82%A8" in query_url
    assert articles == []


@patch("collectors.civil_service.ArticleStore")
@patch("collectors.civil_service._get_now")
@patch("collectors.civil_service.search_civil_service_news")
def test_collect_all_filters_similar_irrelevant_and_old_candidates(
    mock_search: MagicMock,
    mock_now: MagicMock,
    mock_store_cls: MagicMock,
) -> None:
    now = datetime(2026, 9, 23, 7, 0, tzinfo=timezone.utc)
    mock_now.return_value = now
    mock_store_cls.return_value.has_seen.return_value = False
    mock_search.side_effect = [
        [
            _article(
                "정부, 공무원 보수 3% 인상 확정",
                "내년 공무원 보수가 3% 인상된다",
                "https://example.com/new",
                now - timedelta(hours=1),
            ),
            _article(
                "프로야구 포스트시즌 일정 확정",
                "가을 야구 경기 일정이 확정됐다",
                "https://example.com/baseball",
                now - timedelta(hours=2),
            ),
            _article(
                "정부, 추석 연휴 고속도로 통행료 면제 발표",
                "연휴 기간 전국 고속도로 통행료가 면제된다",
                "https://example.com/traffic",
                now - timedelta(hours=2),
            ),
        ],
        [
            _article(
                "공무원 보수 3% 인상 확정 발표",
                "내년 공무원 보수가 3% 인상된다.",
                "https://example.com/duplicate",
                now - timedelta(hours=3),
            )
        ],
    ] + [[]] * 7

    result = collect_all_civil_service()

    assert "정부, 공무원 보수 3% 인상 확정" in result
    assert "공무원 보수 3% 인상 확정 발표" not in result
    assert "프로야구" not in result
    assert "고속도로" not in result
    assert result.count("https://example.com/") == 1


@patch("collectors.civil_service.ArticleStore")
@patch("collectors.civil_service._get_now")
@patch("collectors.civil_service.search_civil_service_news")
def test_collect_all_sorts_newest_first_and_caps_output_at_fifteen(
    mock_search: MagicMock,
    mock_now: MagicMock,
    mock_store_cls: MagicMock,
) -> None:
    now = datetime(2026, 9, 23, 7, 0, tzinfo=timezone.utc)
    mock_now.return_value = now
    store = MagicMock()
    store.has_seen.return_value = False
    mock_store_cls.return_value = store
    candidates = [
        _article(
            f"공무원 정책 개선안 {index}호 발표",
            f"공무원 정책 개선 세부 내용 {index}",
            f"https://example.com/{index}",
            now - timedelta(minutes=index),
        )
        for index in range(1, 19)
    ]
    mock_search.side_effect = [list(reversed(candidates))] + [[]] * 8

    result = collect_all_civil_service()

    assert result.count("https://example.com/") == 15
    assert result.index("개선안 1호") < result.index("개선안 15호")
    assert "개선안 16호" not in result
    assert store.mark_seen.call_count == 15
