from processors.news_selection import build_news_contract, is_valid_news_selection


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
    blocks = [
        (
            f"{position}. [상] 기사 {index}\n"
            f"• 내용 요약: 기사 {index}의 핵심 내용\n"
            "• 실무/영향: 업무에 미치는 영향\n"
            f"🔗 https://example.com/news/{index}"
        )
        for position, index in enumerate(indices, 1)
    ]
    return "\n\n".join(blocks)


def test_contract_caps_twelve_candidates_at_ten() -> None:
    # Given
    raw_news = _raw_news(12)

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 10
    assert contract.fallback_text.count("🔗 http") == 10
    assert "https://example.com/news/10" in contract.fallback_text
    assert "https://example.com/news/11" not in contract.fallback_text


def test_contract_keeps_all_seven_candidates() -> None:
    # Given
    raw_news = _raw_news(7)

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 7
    assert contract.fallback_text.count("🔗 http") == 7


def test_contract_deduplicates_canonical_urls() -> None:
    # Given
    raw_news = _raw_news(2).replace(
        "https://example.com/news/2",
        "https://example.com/news/1?utm_source=briefing#top",
    )

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 1
    assert contract.fallback_text.count("🔗 http") == 1


def test_contract_deduplicates_same_title_from_different_sources() -> None:
    # Given
    raw_news = (
        "[뉴스 수집 결과 - 총 2건]\n\n"
        "1. **동일한 보안 기사** (TechCrunch)\n설명: 첫 기사\n"
        "🔗 https://example.com/one\n\n"
        "2. **동일한 보안 기사** (Wired)\n설명: 둘째 기사\n"
        "🔗 https://example.com/two"
    )

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 1


def test_contract_keeps_distinct_parenthetical_titles() -> None:
    # Given
    raw_news = (
        "[뉴스 수집 결과 - 총 2건]\n\n"
        "1. **보안 취약점 (Windows)** (Wired)\n설명: 윈도우\n"
        "🔗 https://example.com/windows\n\n"
        "2. **보안 취약점 (Linux)** (Wired)\n설명: 리눅스\n"
        "🔗 https://example.com/linux"
    )

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 2


def test_contract_caps_candidates_even_without_descriptions() -> None:
    # Given
    raw_news = _raw_news(12).replace("설명:", "본문:")

    # When
    contract = build_news_contract(raw_news)

    # Then
    assert contract.target_count == 10
    assert contract.fallback_text.count("🔗 http") == 10


def test_validator_accepts_exact_ranked_target() -> None:
    # Given
    contract = build_news_contract(_raw_news(12))
    ranked_news = _ranked_news(list(range(10, 0, -1)))

    # When
    is_valid = is_valid_news_selection(ranked_news, contract)

    # Then
    assert is_valid


def test_validator_rejects_too_few_or_unknown_stories() -> None:
    # Given
    contract = build_news_contract(_raw_news(12))
    too_few = _ranked_news(list(range(9, 0, -1)))
    unknown = _ranked_news(list(range(9, 0, -1)) + [99])

    # When / Then
    assert not is_valid_news_selection(too_few, contract)
    assert not is_valid_news_selection(unknown, contract)


def test_validator_rejects_invented_title_or_blank_analysis() -> None:
    # Given
    contract = build_news_contract(_raw_news(1))
    invented_title = _ranked_news([1]).replace("기사 1", "가짜 기사", 1)
    blank_summary = _ranked_news([1]).replace("기사 1의 핵심 내용", "")
    missing_priority = _ranked_news([1]).replace("[상] ", "")

    # When / Then
    assert not is_valid_news_selection(invented_title, contract)
    assert not is_valid_news_selection(blank_summary, contract)
    assert not is_valid_news_selection(missing_priority, contract)


def test_validator_rejects_malformed_link_or_ranking_order() -> None:
    # Given
    contract = build_news_contract(_raw_news(2))
    valid = _ranked_news([1, 2])
    summary_link = valid.replace(
        "• 내용 요약: 기사 1의 핵심 내용",
        "• 내용 요약: 기사 1의 핵심 내용 https://example.com/news/1",
    ).replace("🔗 https://example.com/news/1\n", "")
    preamble = f"주요 뉴스입니다.\n{valid}"
    trailing_summary = f"{valid}\n\n별도 총평: 오늘의 핵심 뉴스입니다."
    reversed_priority = valid.replace("1. [상]", "1. [하]")

    # When / Then
    assert not is_valid_news_selection(summary_link, contract)
    assert not is_valid_news_selection(preamble, contract)
    assert not is_valid_news_selection(trailing_summary, contract)
    assert not is_valid_news_selection(reversed_priority, contract)
