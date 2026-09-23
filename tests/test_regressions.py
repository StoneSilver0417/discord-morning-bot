import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import requests

from collectors.civil_service import (
    collect_all_civil_service,
    search_civil_service_news,
    search_naver_news,
)
from collectors.it_news import collect_all_it_news
from collectors.stocks import (
    collect_all_stocks,
    collect_naver_finance_news,
    collect_stock_news,
)
from collectors.weather import (
    collect_wind_forecast,
    collect_weather,
    collect_all_weather,
    get_pm10_grade,
    get_pm25_grade,
    get_weather_condition,
)
from formatters.discord_formatter import create_embeds, send_multiple_embeds
from processors.gemini_processor import process_with_gemini
from utils.time_utils import get_kst_now
import main


class RegressionTests(unittest.TestCase):
    def test_kst_date_boundary(self):
        class FakeDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                utc_now = datetime(2026, 7, 14, 15, 0, tzinfo=timezone.utc)
                return utc_now.astimezone(tz) if tz else utc_now

        with patch("utils.time_utils.datetime", FakeDateTime):
            self.assertEqual("2026-07-15", get_kst_now().strftime("%Y-%m-%d"))

    @patch("collectors.weather.requests.get")
    def test_weather_rejects_stale_response_date(self, mocked_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"daily": {"time": ["2026-07-14"]}}
        mocked_get.return_value = response
        with patch("utils.time_utils.get_kst_now") as now:
            now.return_value = datetime(2026, 7, 15, 7, 0, tzinfo=timezone.utc)
            result = collect_wind_forecast("경산 중방동")
        self.assertIn("예보 날짜 불일치", result["error"])

    def test_pm_grading(self):
        self.assertEqual(get_pm10_grade(15), "좋음")
        self.assertEqual(get_pm10_grade(30), "좋음")
        self.assertEqual(get_pm10_grade(31), "보통")
        self.assertEqual(get_pm10_grade(80), "보통")
        self.assertEqual(get_pm10_grade(81), "나쁨")
        self.assertEqual(get_pm10_grade(150), "나쁨")
        self.assertEqual(get_pm10_grade(151), "매우나쁨")
        self.assertEqual(get_pm10_grade(None), "정보없음")

        self.assertEqual(get_pm25_grade(10), "좋음")
        self.assertEqual(get_pm25_grade(15), "좋음")
        self.assertEqual(get_pm25_grade(16), "보통")
        self.assertEqual(get_pm25_grade(35), "보통")
        self.assertEqual(get_pm25_grade(36), "나쁨")
        self.assertEqual(get_pm25_grade(75), "나쁨")
        self.assertEqual(get_pm25_grade(76), "매우나쁨")
        self.assertEqual(get_pm25_grade(None), "정보없음")

    def test_weather_condition_mapping(self):
        self.assertEqual(get_weather_condition(0), "맑음")
        self.assertEqual(get_weather_condition(1), "맑음")
        self.assertEqual(get_weather_condition(2), "구름")
        self.assertEqual(get_weather_condition(3), "구름")
        self.assertEqual(get_weather_condition(61), "비")
        self.assertEqual(get_weather_condition(71), "눈")
        self.assertEqual(get_weather_condition(95), "뇌우")

    @patch("collectors.weather.requests.get")
    def test_collect_weather_success(self, mocked_get):
        weather_resp = Mock()
        weather_resp.raise_for_status.return_value = None
        weather_resp.json.return_value = {
            "current": {
                "temperature_2m": 25.0,
                "apparent_temperature": 27.0,
                "relative_humidity_2m": 60,
                "precipitation": 0.0,
                "wind_speed_10m": 5.0,
                "wind_direction_10m": 180,
                "surface_pressure": 1013.0,
                "weather_code": 1,
            },
            "daily": {
                "time": ["2026-09-02"],
                "temperature_2m_max": [29.0],
                "temperature_2m_min": [20.0],
                "precipitation_probability_max": [20],
                "uv_index_max": [5.5],
            },
            "hourly": {
                "time": ["2026-09-02T08:00", "2026-09-02T12:00", "2026-09-02T18:00"],
                "temperature_2m": [22.0, 28.0, 24.0],
                "weather_code": [1, 1, 2],
            },
        }
        air_resp = Mock()
        air_resp.raise_for_status.return_value = None
        air_resp.json.return_value = {
            "current": {
                "pm10": 25.4,
                "pm2_5": 12.1,
            }
        }
        mocked_get.side_effect = [weather_resp, air_resp]

        with patch("utils.time_utils.get_kst_now") as now:
            now.return_value = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
            result = collect_weather("경산 중방동")

        self.assertEqual(result["current_temp"], 25.0)
        self.assertEqual(result["apparent_temp"], 27.0)
        self.assertEqual(result["pm10_grade"], "좋음")
        self.assertEqual(result["pm2_5_grade"], "좋음")
        self.assertIn("미세: 25㎍/㎥ (좋음)", result["dust"])
        self.assertIn("초미세: 12㎍/㎥ (좋음)", result["dust"])

    @patch("collectors.it_news.collect_hackernews", return_value=[])
    @patch("collectors.it_news.collect_rss_feeds", return_value=[])
    def test_empty_it_news_is_failure(self, _rss, _hn):
        with self.assertRaises(RuntimeError):
            collect_all_it_news()

    @patch("collectors.civil_service.search_civil_service_news", return_value=[])
    def test_empty_civil_news_is_failure(self, _search):
        with self.assertRaises(RuntimeError):
            collect_all_civil_service()

    @patch(
        "collectors.it_news.collect_hackernews",
        return_value=[
            {
                "source": "HN",
                "title": "테스트 기사",
                "link": "https://example.com/news",
                "summary": "기사 핵심 설명",
            }
        ],
    )
    @patch("collectors.it_news.collect_rss_feeds", return_value=[])
    def test_it_news_includes_summary_for_one_line_generation(self, _rss, _hn):
        result = collect_all_it_news()
        self.assertIn("설명: 기사 핵심 설명", result)
        self.assertIn("https://example.com/news", result)

    @patch(
        "collectors.civil_service.search_civil_service_news",
        return_value=[
            {
                "title": "공무원 테스트 기사",
                "link": "https://example.com/civil",
                "summary": "공무원에게 미치는 영향",
            }
        ],
    )
    def test_civil_news_includes_summary_for_one_line_generation(self, _search):
        result = collect_all_civil_service()
        self.assertIn("설명: 공무원에게 미치는 영향", result)
        self.assertIn("https://example.com/civil", result)

    def test_civil_service_news_aliases(self):
        self.assertIs(search_naver_news, search_civil_service_news)

    @patch("collectors.civil_service.feedparser.parse")
    def test_civil_service_rss_bozo_error_returns_empty(self, mocked_parse):
        feed = Mock()
        feed.bozo = True
        feed.entries = []
        feed.get.return_value = "SyntaxError"
        mocked_parse.return_value = feed

        articles = search_civil_service_news("공무원 정책")
        self.assertEqual(articles, [])

    @patch("collectors.civil_service.feedparser.parse")
    def test_civil_service_rss_exception_returns_empty(self, mocked_parse):
        mocked_parse.side_effect = Exception("Network timeout")
        articles = search_civil_service_news("공무원 정책")
        self.assertEqual(articles, [])

    @patch("collectors.civil_service.feedparser.parse")
    def test_civil_service_rss_cleaning_and_parsing(self, mocked_parse):
        feed = Mock()
        feed.bozo = False
        feed.entries = [
            {
                "title": "<b>공무원</b> &quot;처우&quot; &amp; 급여 &apos;개선&apos;",
                "summary": "정부가 <b>공무원</b> 처우를 <b>개선</b> &lt;합의&gt;",
                "link": "https://news.google.com/rss/articles/CBMi1",
                "published": "Wed, 02 Sep 2026 09:00:00 GMT",
            },
            {
                "title": "전산직 <b>채용</b> 공고",
                "description": "전산직 공무원 <b>선발</b> 공고",
                "link": "https://news.google.com/rss/articles/CBMi2",
                "pubDate": "Wed, 02 Sep 2026 10:00:00 GMT",
            },
            {
                "title": "링크 없음",
                "link": "",
                "summary": "설명",
            },
        ]
        mocked_parse.return_value = feed

        articles = search_civil_service_news("공무원", count=5)

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], '공무원 "처우" & 급여 \'개선\'')
        self.assertEqual(articles[0]["summary"], "정부가 공무원 처우를 개선 <합의>")
        self.assertEqual(articles[0]["link"], "https://news.google.com/rss/articles/CBMi1")
        self.assertEqual(articles[0]["pubDate"], "Wed, 02 Sep 2026 09:00:00 GMT")
        self.assertEqual(articles[0]["keyword"], "공무원")

        self.assertEqual(articles[1]["title"], "전산직 채용 공고")
        self.assertEqual(articles[1]["summary"], "전산직 공무원 선발 공고")
        self.assertEqual(articles[1]["link"], "https://news.google.com/rss/articles/CBMi2")
        self.assertEqual(articles[1]["pubDate"], "Wed, 02 Sep 2026 10:00:00 GMT")

        mocked_parse.assert_called_once()
        call_url = mocked_parse.call_args[0][0]
        self.assertIn("https://news.google.com/rss/search?q=", call_url)
        self.assertIn("hl=ko", call_url)

    @patch("collectors.civil_service.search_civil_service_news")
    def test_collect_all_civil_service_dedup_and_prioritization(self, mocked_search):
        mocked_search.side_effect = [
            [
                {"title": "공무원 처우 개선 종합 대책", "link": "https://ex.com/1", "summary": "설명1"},
                {"title": "짧음", "link": "https://ex.com/2", "summary": "5자 미만"},
            ],
            [
                {"title": "공무원 처우 개선 종합 대책", "link": "https://ex.com/1-dup", "summary": "중복 기사"},
                {"title": "전산직 공무원 신규 채용 규모 확대", "link": "https://ex.com/3", "summary": ""},
            ],
            [
                {"title": "사회복지직 공무원 수당 인상 결정", "link": "https://ex.com/4", "summary": "설명4"},
            ],
            [],
            [],
            [],
            [],
            [],
            [],
        ]

        result = collect_all_civil_service()
        self.assertIn("공무원 처우 개선 종합 대책", result)
        self.assertIn("사회복지직 공무원 수당 인상 결정", result)
        self.assertIn("전산직 공무원 신규 채용 규모 확대", result)
        self.assertNotIn("짧음", result)
        self.assertNotIn("1-dup", result)

    def test_stock_news_aliases(self):
        self.assertIs(collect_naver_finance_news, collect_stock_news)

    @patch("collectors.stocks.feedparser.parse")
    def test_stock_news_rss_bozo_empty_returns_fallback(self, mocked_parse):
        feed = Mock()
        feed.bozo = True
        feed.entries = []
        feed.get.return_value = "XML error"
        mocked_parse.return_value = feed

        result = collect_stock_news()
        self.assertIn("뉴스를 가져올 수 없습니다.", result)

    @patch("collectors.stocks.feedparser.parse")
    def test_stock_news_rss_exception_returns_fallback(self, mocked_parse):
        mocked_parse.side_effect = Exception("Connection error")
        result = collect_stock_news()
        self.assertIn("뉴스 수집 실패", result)

    @patch("collectors.stocks.feedparser.parse")
    def test_stock_news_rss_cleaning_dedup_and_format(self, mocked_parse):
        feed = Mock()
        feed.bozo = False
        feed.entries = [
            {
                "title": "코스피 <b>외국인</b> &quot;순매수&quot; &amp; 상승",
                "summary": "외국인 매수세에 힘입어 <b>코스피</b> 지수 &apos;상승&apos;",
                "link": "https://news.google.com/rss/articles/CBMi1",
            },
            {
                "title": "코스피 <b>외국인</b> &quot;순매수&quot; &amp; 상승",
                "summary": "중복 기사 설명",
                "link": "https://news.google.com/rss/articles/CBMi1-dup",
            },
            {
                "title": "단신",
                "summary": "너무 짧은 기사",
                "link": "https://news.google.com/rss/articles/short",
            },
            {
                "title": "뉴욕증시 <b>혼조세</b> 마감",
                "description": "금리 인하 기대감 속 <b>혼조</b> 마감",
                "link": "https://news.google.com/rss/articles/CBMi2",
            },
        ]
        mocked_parse.return_value = feed

        result = collect_stock_news()

        self.assertIn('코스피 외국인 "순매수" & 상승', result)
        self.assertIn("외국인 매수세에 힘입어 코스피 지수 '상승'", result)
        self.assertIn("https://news.google.com/rss/articles/CBMi1", result)
        self.assertIn("뉴욕증시 혼조세 마감", result)
        self.assertIn("https://news.google.com/rss/articles/CBMi2", result)
        self.assertNotIn("단신", result)
        self.assertNotIn("CBMi1-dup", result)

        mocked_parse.assert_called_once()
        call_url = mocked_parse.call_args[0][0]
        self.assertIn("https://news.google.com/rss/search?q=", call_url)
        self.assertIn("hl=ko", call_url)

    @patch("collectors.stocks.collect_index_data", return_value="[주요 지수 현황]\n  KOSPI: 2,600.00\n")
    @patch("collectors.stocks.collect_korean_market", return_value="\n[한국 시장 상세]\n  시가총액 상위 10 종목:\n    삼성전자: +1.5%\n")
    @patch("collectors.stocks.collect_stock_news", return_value="\n[증권 주요 뉴스]\n  • 코스피 상승세 지속\n")
    def test_collect_all_stocks_combines_all_sections(self, mock_news, mock_market, mock_idx):
        result = collect_all_stocks()
        self.assertIn("[주요 지수 현황]", result)
        self.assertIn("KOSPI: 2,600.00", result)
        self.assertIn("[한국 시장 상세]", result)
        self.assertIn("삼성전자: +1.5%", result)
        self.assertIn("[증권 주요 뉴스]", result)
        self.assertIn("코스피 상승세 지속", result)

    def test_empty_input_is_not_sent_to_gemini(self):
        with self.assertRaises(ValueError):
            process_with_gemini("it_news", "  ")

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_failure_is_not_treated_as_success(self, mocked_client):
        mocked_client.return_value.models.generate_content.side_effect = RuntimeError("API failure")
        with self.assertRaises(RuntimeError):
            process_with_gemini("it_news", "뉴스 원문")

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_quota_exhaustion_returns_full_raw_news(self, mocked_client):
        raw_news = "[IT 뉴스 수집 결과]\n\n" + "\n\n".join(
            f"{index}. **기사{index}** (테스트)\n설명: 요약{index}\n"
            f"🔗 https://example.com/{index}"
            for index in range(1, 13)
        )
        mocked_client.return_value.models.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(10, result.count("🔗 http"))
        self.assertNotIn("https://example.com/11", result)

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_service_unavailable_returns_full_raw_data(self, mocked_client):
        raw_weather = "완전한 원문 날씨 데이터"
        mocked_client.return_value.models.generate_content.side_effect = RuntimeError(
            "503 UNAVAILABLE: model is experiencing high demand"
        )

        self.assertEqual(raw_weather, process_with_gemini("weather", raw_weather))

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_incomplete_gemini_response_returns_full_raw_news(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1"
        )
        response = Mock()
        response.text = "중간에 잘린 AI 응답"
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(1, result.count("🔗 http"))

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_invalid_news_list_returns_full_raw_news(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1"
        )
        response = Mock()
        response.text = "1. 첫 기사 제목만 있고 요약이나 링크가 전혀 없는 불완전한 결과"
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(1, result.count("🔗 http"))

    def test_long_discord_description_is_split_without_loss(self):
        content = "A" * 4096 + "\n" + "B" * 1000
        embeds = create_embeds("it_news", "뉴스", content)
        self.assertEqual(2, len(embeds))
        self.assertTrue(all(len(embed["description"]) <= 4096 for embed in embeds))
        self.assertEqual(content, "".join(e["description"] for e in embeds))

    @patch("formatters.discord_formatter.send_webhook", return_value=True)
    def test_split_embeds_are_sent_in_separate_messages(self, mocked_send):
        embeds = create_embeds("it_news", "뉴스", "A" * 9000)
        self.assertTrue(send_multiple_embeds("https://example.invalid", embeds))
        self.assertEqual(len(embeds), mocked_send.call_count)
        self.assertTrue(all(len(call.kwargs["embeds"]) == 1 for call in mocked_send.call_args_list))

    @patch("main.time.sleep")
    @patch("main.send_multiple_embeds", return_value=False)
    @patch("main.create_embeds", return_value=[{"description": "ok"}])
    @patch("main.process_with_gemini", return_value="요약")
    @patch("main.collect_all_civil_service", return_value="뉴스")
    @patch("main.collect_all_it_news", return_value="뉴스")
    @patch("main.collect_all_stocks", return_value="주식")
    @patch("main.collect_all_weather", return_value="날씨")
    def test_webhook_failure_makes_run_fail(self, *_mocks):
        with (
            patch.object(main.Config, "DISCORD_WEBHOOK_MAIN", "https://example.invalid"),
            patch.object(main.Config, "DISCORD_WEBHOOK_WEATHER", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_STOCKS", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_IT_NEWS", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_CIVIL_SERVICE", ""),
        ):
            self.assertFalse(main.run_briefing())

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_uses_category_model(self, mocked_client):
        response = Mock()
        response.text = "가공된 결과"
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        process_with_gemini("weather", "날씨 원문")
        mocked_client.return_value.models.generate_content.assert_called_with(
            model="gemini-3.6-flash",
            contents=unittest.mock.ANY,
            config=unittest.mock.ANY,
        )

        mocked_client.return_value.models.generate_content.reset_mock()
        response.text = (
            "1. 기사1\n→ 요약1\n🔗 https://example.com/1\n"
            "2. 기사2\n→ 요약2\n🔗 https://example.com/2\n"
            "3. 기사3\n→ 요약3\n🔗 https://example.com/3"
        )
        with patch.object(main.Config, "GEMINI_MODEL_IT_NEWS", "gemini-3.1-pro-preview"):
            process_with_gemini("it_news", "IT뉴스 원문")
            mocked_client.return_value.models.generate_content.assert_called_with(
                model="gemini-3.1-pro-preview",
                contents=unittest.mock.ANY,
                config=unittest.mock.ANY,
            )

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_fallback_on_404(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과 - 총 2건]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1\n\n"
            "2. **기사2** (테스트)\n설명: 요약2\n🔗 https://example.com/2"
        )
        response = Mock()
        response.text = (
            "1. [상] 기사1\n• 내용 요약: 요약1\n• 실무/영향: 영향1\n🔗 https://example.com/1\n"
            "2. [중] 기사2\n• 내용 요약: 요약2\n• 실무/영향: 영향2\n🔗 https://example.com/2"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.side_effect = [
            RuntimeError("404 Not Found: models/gemini-3.1-pro-preview is not found"),
            response,
        ]

        with patch.object(main.Config, "GEMINI_MODEL_IT_NEWS", "gemini-3.1-pro-preview"):
            result = process_with_gemini("it_news", raw_news)
        self.assertEqual(response.text, result)
        self.assertEqual(2, mocked_client.return_value.models.generate_content.call_count)
        first_call = mocked_client.return_value.models.generate_content.call_args_list[0]
        second_call = mocked_client.return_value.models.generate_content.call_args_list[1]
        self.assertEqual("gemini-3.1-pro-preview", first_call.kwargs["model"])
        self.assertEqual("gemini-3.6-flash", second_call.kwargs["model"])

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_fallback_on_429(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과 - 총 2건]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1\n\n"
            "2. **기사2** (테스트)\n설명: 요약2\n🔗 https://example.com/2"
        )
        response = Mock()
        response.text = (
            "1. [상] 기사1\n"
            "   • 내용 요약: 핵심 내용 요약1\n"
            "   • 실무/영향: 공무원 또는 IT 실무에 미치는 영향1\n"
            "   🔗 https://example.com/1\n"
            "2. [중] 기사2\n"
            "   • 내용 요약: 핵심 내용 요약2\n"
            "   • 실무/영향: 공무원 또는 IT 실무에 미치는 영향2\n"
            "   🔗 https://example.com/2"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.side_effect = [
            RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"),
            response,
        ]

        with patch.object(main.Config, "GEMINI_MODEL_IT_NEWS", "gemini-3.1-pro-preview"):
            result = process_with_gemini("it_news", raw_news)
        self.assertEqual(response.text, result)
        self.assertEqual(2, mocked_client.return_value.models.generate_content.call_count)
        first_call = mocked_client.return_value.models.generate_content.call_args_list[0]
        second_call = mocked_client.return_value.models.generate_content.call_args_list[1]
        self.assertEqual("gemini-3.1-pro-preview", first_call.kwargs["model"])
        self.assertEqual("gemini-3.6-flash", second_call.kwargs["model"])

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_news_list_detailed_format_accepted(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과 - 총 2건]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1\n\n"
            "2. **기사2** (테스트)\n설명: 요약2\n🔗 https://example.com/2"
        )
        response = Mock()
        response.text = (
            "1. [상] 기사1\n"
            "   • 내용 요약: 핵심 내용 요약1\n"
            "   • 실무/영향: 공무원 또는 IT 실무에 미치는 영향1\n"
            "   🔗 https://example.com/1\n"
            "2. [중] 기사2\n"
            "   • 내용 요약: 핵심 내용 요약2\n"
            "   • 실무/영향: 공무원 또는 IT 실무에 미치는 영향2\n"
            "   🔗 https://example.com/2"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(response.text, result)

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_news_list_missing_link_rejected(self, mocked_client):
        raw_news = (
            "[IT 뉴스 수집 결과]\n\n"
            "1. **기사1** (테스트)\n설명: 요약1\n🔗 https://example.com/1\n\n"
            "2. **기사2** (테스트)\n설명: 요약2\n🔗 https://example.com/2"
        )
        response = Mock()
        response.text = (
            "1. [보안] 기사1\n"
            "   • 내용 요약: 핵심 내용 요약1\n"
            "   • 실무/영향: 실무 영향1\n"
            "2. [클라우드] 기사2\n"
            "   • 내용 요약: 핵심 내용 요약2\n"
            "   • 실무/영향: 실무 영향2"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(2, result.count("🔗 http"))

    def test_is_model_not_found_detection(self):
        from processors.gemini_processor import _is_model_not_found
        self.assertTrue(_is_model_not_found(RuntimeError("404 Not Found: model is not found")))
        self.assertTrue(_is_model_not_found(Exception("models/gemini-3.1-pro-preview is not supported")))
        self.assertFalse(_is_model_not_found(RuntimeError("500 Internal Server Error")))

    def test_is_quota_exhausted_detection(self):
        from processors.gemini_processor import _is_quota_exhausted
        self.assertTrue(_is_quota_exhausted(RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")))
        self.assertTrue(_is_quota_exhausted(Exception("ResourceExhausted: Quota exceeded for metric")))
        self.assertFalse(_is_quota_exhausted(RuntimeError("500 Internal Server Error")))

    @patch("main.time.sleep")
    @patch("main.send_multiple_embeds", return_value=True)
    @patch("main.create_embeds", return_value=[{"description": "ok"}])
    @patch("main.process_with_gemini", return_value="요약")
    @patch("main.collect_all_civil_service", return_value="뉴스")
    @patch("main.collect_all_it_news", return_value="뉴스")
    @patch("main.collect_all_stocks", return_value="주식")
    @patch("main.collect_all_weather", return_value="날씨")
    def test_main_category_delays_35s(self, _weather, _stocks, _it, _civil, _gemini, _embeds, _send, mock_sleep):
        with (
            patch.object(main.Config, "DISCORD_WEBHOOK_MAIN", "https://example.invalid"),
            patch.object(main.Config, "DISCORD_WEBHOOK_WEATHER", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_STOCKS", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_IT_NEWS", ""),
            patch.object(main.Config, "DISCORD_WEBHOOK_CIVIL_SERVICE", ""),
        ):
            success = main.run_briefing()
            self.assertTrue(success)
            sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
            self.assertEqual(3, sleep_args.count(35))

    def test_empty_model_env_vars_fallback_to_defaults(self):
        import importlib
        import os
        import config

        empty_env = {
            "GEMINI_MODEL_WEATHER": "",
            "GEMINI_MODEL_STOCKS": "",
            "GEMINI_MODEL_IT_NEWS": "",
            "GEMINI_MODEL_CIVIL_SERVICE": "",
            "GEMINI_MODEL_FALLBACK": "",
        }
        with patch.dict(os.environ, empty_env, clear=False):
            reloaded_config = importlib.reload(config)
            cfg = reloaded_config.Config
            self.assertEqual("gemini-3.6-flash", cfg.GEMINI_MODEL_WEATHER)
            self.assertEqual("gemini-3.6-flash", cfg.GEMINI_MODEL_STOCKS)
            self.assertEqual("gemini-3.6-flash", cfg.GEMINI_MODEL_IT_NEWS)
            self.assertEqual("gemini-3.6-flash", cfg.GEMINI_MODEL_CIVIL_SERVICE)
            self.assertEqual("gemini-3.6-flash", cfg.GEMINI_MODEL_FALLBACK)
            self.assertEqual("gemini-3.6-flash", cfg.get_model_for_category("weather"))
            self.assertEqual("gemini-3.6-flash", cfg.get_model_for_category("stocks"))
            self.assertEqual("gemini-3.6-flash", cfg.get_model_for_category("it_news"))
            self.assertEqual("gemini-3.6-flash", cfg.get_model_for_category("civil_service"))

        importlib.reload(config)

    def test_get_model_for_category_never_returns_empty_or_whitespace(self):
        from config import Config

        with (
            patch.object(Config, "GEMINI_MODEL_WEATHER", ""),
            patch.object(Config, "GEMINI_MODEL_STOCKS", "   "),
            patch.object(Config, "GEMINI_MODEL_IT_NEWS", None),
            patch.object(Config, "GEMINI_MODEL_CIVIL_SERVICE", ""),
            patch.object(Config, "GEMINI_MODEL_FALLBACK", "  "),
        ):
            for cat in ["weather", "stocks", "it_news", "civil_service", "", "  ", None, "unknown_category"]:
                model = Config.get_model_for_category(cat)
                self.assertTrue(bool(model))
                self.assertTrue(bool(model.strip()))
                self.assertEqual(model, model.strip())


class ArticleStoreTests(unittest.TestCase):
    """RED→GREEN tests for the stale/duplicate-news fix (utils/article_store)."""

    def _make_articles(self, urls_and_ages):
        from datetime import datetime, timezone, timedelta
        now = datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
        articles = []
        for i, (url, age_hours) in enumerate(urls_and_ages):
            articles.append({
                "source": "TestSource",
                "title": f"Article {i}",
                "link": url,
                "summary": "summary",
                "published_at": now - timedelta(hours=age_hours),
            })
        return articles, now

    def test_no_fresh_articles_error_is_importable(self):
        from utils.article_store import NoFreshArticlesError
        self.assertTrue(issubclass(NoFreshArticlesError, Exception))

    # --- URL canonicalization ---

    def test_canonicalize_strips_fragment(self):
        from utils.article_store import canonicalize_url
        self.assertEqual(
            "https://example.com/news",
            canonicalize_url("https://example.com/news#section"),
        )

    def test_canonicalize_strips_utm_params(self):
        from utils.article_store import canonicalize_url
        url = "https://example.com/news?utm_source=twitter&utm_medium=social&real=1"
        canon = canonicalize_url(url)
        self.assertNotIn("utm_source", canon)
        self.assertNotIn("utm_medium", canon)
        self.assertIn("real=1", canon)

    def test_canonicalize_strips_fbclid_and_gclid(self):
        from utils.article_store import canonicalize_url
        url = "https://example.com/news?fbclid=xyz&gclid=abc"
        canon = canonicalize_url(url)
        self.assertNotIn("fbclid", canon)
        self.assertNotIn("gclid", canon)

    def test_canonicalize_stable_for_same_url(self):
        from utils.article_store import canonicalize_url
        url = "https://example.com/news?a=1&b=2"
        self.assertEqual(canonicalize_url(url), canonicalize_url(url))

    # --- ArticleStore load/save ---

    def test_store_loads_missing_file_as_empty(self):
        import tempfile, os
        from utils.article_store import ArticleStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nonexistent.json")
            store = ArticleStore(path)
            self.assertEqual({}, store.seen)

    def test_store_handles_malformed_json_safely(self):
        import tempfile, os
        from utils.article_store import ArticleStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            with open(path, "w") as f:
                f.write("{NOT VALID JSON")
            store = ArticleStore(path)
            self.assertEqual({}, store.seen)

    def test_store_handles_wrong_type_json_safely(self):
        import tempfile, os, json
        from utils.article_store import ArticleStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "wrong.json")
            with open(path, "w") as f:
                json.dump([1, 2, 3], f)  # list instead of dict
            store = ArticleStore(path)
            self.assertEqual({}, store.seen)

    def test_store_save_and_reload(self):
        import tempfile, os
        from datetime import datetime, timezone
        from utils.article_store import ArticleStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "seen.json")
            store = ArticleStore(path)
            ts = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
            store.mark_seen("it_news", "https://example.com/1", ts)
            store.save()
            store2 = ArticleStore(path)
            self.assertIn("https://example.com/1", store2.seen.get("it_news", {}))

    def test_store_atomic_write_does_not_corrupt_on_partial(self):
        """Save should use atomic write (temp file + rename)."""
        import tempfile, os
        from datetime import datetime, timezone
        from utils.article_store import ArticleStore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "seen.json")
            store = ArticleStore(path)
            ts = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
            store.mark_seen("it_news", "https://example.com/1", ts)
            store.save()
            # File must be valid JSON after save
            import json
            with open(path) as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)

    # --- freshness filter ---

    def test_filter_fresh_keeps_articles_within_window(self):
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/new", 1),   # 1h ago — fresh
            ("https://example.com/old", 50),  # 50h ago — stale
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            fresh = filter_fresh(articles, store, "it_news", now=now, max_age_hours=48)
        self.assertEqual(1, len(fresh))
        self.assertEqual("https://example.com/new", fresh[0]["link"])

    def test_filter_fresh_excludes_seen_urls(self):
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/1", 1),
            ("https://example.com/2", 2),
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            store.mark_seen("it_news", "https://example.com/1", now)
            fresh = filter_fresh(articles, store, "it_news", now=now, max_age_hours=48)
        self.assertEqual(1, len(fresh))
        self.assertEqual("https://example.com/2", fresh[0]["link"])

    def test_filter_fresh_dedupes_by_canonical_url(self):
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/a?utm_source=x", 1),
            ("https://example.com/a", 2),  # same canonical
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            fresh = filter_fresh(articles, store, "it_news", now=now, max_age_hours=48)
        self.assertEqual(1, len(fresh))

    def test_filter_fresh_sorts_newest_first(self):
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/older", 10),
            ("https://example.com/newer", 1),
            ("https://example.com/middle", 5),
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            fresh = filter_fresh(articles, store, "it_news", now=now, max_age_hours=48)
        links = [a["link"] for a in fresh]
        self.assertEqual(["https://example.com/newer", "https://example.com/middle", "https://example.com/older"], links)

    def test_filter_fresh_all_seen_returns_empty(self):
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/1", 1),
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            store.mark_seen("it_news", "https://example.com/1", now)
            fresh = filter_fresh(articles, store, "it_news", now=now, max_age_hours=48)
        self.assertEqual([], fresh)

    def test_filter_fresh_default_window_is_48h(self):
        """filter_fresh with no max_age_hours should default to 48h."""
        from utils.article_store import ArticleStore, filter_fresh
        import tempfile, os
        articles, now = self._make_articles([
            ("https://example.com/fresh", 47),
            ("https://example.com/stale", 49),
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            fresh = filter_fresh(articles, store, "it_news", now=now)
        self.assertEqual(1, len(fresh))
        self.assertEqual("https://example.com/fresh", fresh[0]["link"])

    # --- prune history ---

    def test_store_prune_removes_old_entries(self):
        import tempfile, os
        from datetime import datetime, timezone, timedelta
        from utils.article_store import ArticleStore
        now = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArticleStore(os.path.join(tmpdir, "seen.json"))
            store.mark_seen("it_news", "https://example.com/old", now - timedelta(hours=200))
            store.mark_seen("it_news", "https://example.com/new", now - timedelta(hours=10))
            store.prune(now=now, max_age_hours=48)
            self.assertNotIn("https://example.com/old", store.seen.get("it_news", {}))
            self.assertIn("https://example.com/new", store.seen.get("it_news", {}))

    # --- collector timestamp capture ---

    def test_it_news_rss_article_has_published_at(self):
        """collect_rss_feeds must include published_at (datetime) in each article."""
        from unittest.mock import patch, MagicMock
        import feedparser
        from collectors.it_news import collect_rss_feeds

        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Test Article",
            "link": "https://example.com/it",
            "summary": "summary",
            "published": "Mon, 21 Sep 2026 05:00:00 GMT",
        }.get(key, default)
        mock_entry.__contains__ = lambda self, key: key in {"title", "link", "summary", "published"}

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("collectors.it_news.feedparser.parse", return_value=mock_feed):
            articles = collect_rss_feeds()

        self.assertTrue(len(articles) >= 1)
        art = articles[0]
        self.assertIn("published_at", art)
        from datetime import datetime
        self.assertIsInstance(art["published_at"], datetime)

    def test_hackernews_article_has_published_at(self):
        """collect_hackernews must include published_at (datetime) from HN `time` field."""
        from unittest.mock import patch
        import time as time_module
        from collectors.it_news import collect_hackernews

        story_ids = [12345]
        story_item = {
            "id": 12345,
            "title": "HN Article",
            "url": "https://hn-example.com",
            "score": 100,
            "descendants": 50,
            "time": 1758488400,  # a Unix timestamp
        }

        with patch("collectors.it_news.requests.get") as mock_get:
            resp_ids = MagicMock()
            resp_ids.json.return_value = story_ids
            resp_item = MagicMock()
            resp_item.json.return_value = story_item
            mock_get.side_effect = [resp_ids, resp_item]

            articles = collect_hackernews()

        self.assertEqual(1, len(articles))
        self.assertIn("published_at", articles[0])
        from datetime import datetime
        self.assertIsInstance(articles[0]["published_at"], datetime)

    def test_rss_article_missing_date_is_rejected(self):
        """RSS articles with no parseable date must be excluded."""
        from unittest.mock import patch, MagicMock
        from collectors.it_news import collect_rss_feeds

        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "No Date Article",
            "link": "https://example.com/nodate",
            "summary": "summary",
        }.get(key, default)

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("collectors.it_news.feedparser.parse", return_value=mock_feed):
            articles = collect_rss_feeds()

        # No article without a parseable date should appear
        for art in articles:
            self.assertIn("published_at", art)

    def test_hackernews_article_missing_time_is_rejected(self):
        """HN items without a `time` field must be excluded."""
        from unittest.mock import patch, MagicMock
        from collectors.it_news import collect_hackernews

        story_ids = [99999]
        story_item = {
            "id": 99999,
            "title": "HN No Time",
            "url": "https://hn-example.com",
            "score": 50,
            "descendants": 10,
            # no "time" key
        }

        with patch("collectors.it_news.requests.get") as mock_get:
            resp_ids = MagicMock()
            resp_ids.json.return_value = story_ids
            resp_item = MagicMock()
            resp_item.json.return_value = story_item
            mock_get.side_effect = [resp_ids, resp_item]

            articles = collect_hackernews()

        self.assertEqual(0, len(articles))

    def test_civil_service_rss_article_has_published_at(self):
        """search_civil_service_news must include published_at (datetime) in each article."""
        from unittest.mock import patch, MagicMock
        from collectors.civil_service import search_civil_service_news

        mock_entry = {
            "title": "공무원 테스트",
            "link": "https://news.google.com/rss/articles/CBMi1",
            "summary": "설명",
            "published": "Mon, 21 Sep 2026 05:00:00 GMT",
        }

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]

        with patch("collectors.civil_service.feedparser.parse", return_value=mock_feed):
            articles = search_civil_service_news("공무원")

        self.assertEqual(1, len(articles))
        self.assertIn("published_at", articles[0])
        from datetime import datetime
        self.assertIsInstance(articles[0]["published_at"], datetime)

    def test_civil_service_article_missing_date_is_rejected(self):
        """Civil service RSS articles with no parseable date must be excluded."""
        from unittest.mock import patch, MagicMock
        from collectors.civil_service import search_civil_service_news

        mock_entry = {
            "title": "날짜없는 공무원 기사",
            "link": "https://news.google.com/rss/articles/CBMi2",
            "summary": "설명",
            # no published or pubDate
        }

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]

        with patch("collectors.civil_service.feedparser.parse", return_value=mock_feed):
            articles = search_civil_service_news("공무원")

        # All returned articles must have a published_at
        for art in articles:
            self.assertIn("published_at", art)
        # The entry with no date must be excluded
        self.assertEqual(0, len(articles))

    # --- existing fixture compatibility: pubDate still returned ---

    def test_civil_service_rss_cleaning_and_parsing_still_works(self):
        """Existing shape tests still pass after adding published_at."""
        from unittest.mock import patch, MagicMock
        from collectors.civil_service import search_civil_service_news

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                "title": "<b>공무원</b> &quot;처우&quot; &amp; 급여 &apos;개선&apos;",
                "summary": "정부가 <b>공무원</b> 처우를 <b>개선</b> &lt;합의&gt;",
                "link": "https://news.google.com/rss/articles/CBMi1",
                "published": "Wed, 02 Sep 2026 09:00:00 GMT",
            },
            {
                "title": "전산직 <b>채용</b> 공고",
                "description": "전산직 공무원 <b>선발</b> 공고",
                "link": "https://news.google.com/rss/articles/CBMi2",
                "pubDate": "Wed, 02 Sep 2026 10:00:00 GMT",
            },
            {
                "title": "링크 없음",
                "link": "",
                "summary": "설명",
                "published": "Wed, 02 Sep 2026 08:00:00 GMT",
            },
        ]
        with patch("collectors.civil_service.feedparser.parse", return_value=mock_feed):
            articles = search_civil_service_news("공무원", count=5)

        self.assertEqual(2, len(articles))
        self.assertEqual(articles[0]["title"], '공무원 "처우" & 급여 \'개선\'')
        self.assertEqual(articles[0]["summary"], "정부가 공무원 처우를 개선 <합의>")
        self.assertIn("published_at", articles[0])

    # --- collect_all_it_news: NoFreshArticlesError when all seen ---

    def test_it_news_raises_no_fresh_when_all_seen(self):
        """collect_all_it_news raises NoFreshArticlesError when all articles already seen."""
        from utils.article_store import NoFreshArticlesError, ArticleStore
        from unittest.mock import patch, MagicMock
        import tempfile, os
        from datetime import datetime, timezone

        now = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
        article = {
            "source": "HN",
            "title": "Already Seen",
            "link": "https://example.com/seen",
            "summary": "x",
            "published_at": now,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, "seen.json")
            store = ArticleStore(store_path)
            store.mark_seen("it_news", "https://example.com/seen", now)
            store.save()

            with (
                patch("collectors.it_news.collect_hackernews", return_value=[article]),
                patch("collectors.it_news.collect_rss_feeds", return_value=[]),
                patch("collectors.it_news.ARTICLE_STORE_PATH", store_path),
                patch("collectors.it_news._get_now", return_value=now),
            ):
                with self.assertRaises(NoFreshArticlesError):
                    from collectors import it_news
                    it_news.collect_all_it_news()

    # --- collect_all_civil_service: NoFreshArticlesError when all seen ---

    def test_civil_news_raises_no_fresh_when_all_seen(self):
        """collect_all_civil_service raises NoFreshArticlesError when all articles already seen."""
        from utils.article_store import NoFreshArticlesError, ArticleStore
        from unittest.mock import patch, MagicMock
        import tempfile, os
        from datetime import datetime, timezone

        now = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
        article = {
            "title": "공무원 기사",
            "link": "https://example.com/civil-seen",
            "summary": "설명",
            "pubDate": "Mon, 21 Sep 2026 07:00:00 GMT",
            "keyword": "공무원",
            "published_at": now,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, "seen.json")
            store = ArticleStore(store_path)
            store.mark_seen("civil_service", "https://example.com/civil-seen", now)
            store.save()

            with (
                patch("collectors.civil_service.search_civil_service_news", return_value=[article]),
                patch("collectors.civil_service.ARTICLE_STORE_PATH", store_path),
                patch("collectors.civil_service._get_now", return_value=now),
            ):
                with self.assertRaises(NoFreshArticlesError):
                    from collectors import civil_service
                    civil_service.collect_all_civil_service()


class ITNewsCollectorTests(unittest.TestCase):
    """TDD tests for IT news collection behaviour (RSS + HackerNews)."""

    # ── 1. Config: at least 6 RSS feeds configured ───────────────────────────

    def test_it_news_feeds_has_at_least_six_entries(self):
        """Config.IT_NEWS_FEEDS must have ≥ 6 feeds so the collector has diverse sources."""
        from config import Config
        self.assertGreaterEqual(
            len(Config.IT_NEWS_FEEDS),
            6,
            f"Expected ≥6 feeds, got {len(Config.IT_NEWS_FEEDS)}: {[f['name'] for f in Config.IT_NEWS_FEEDS]}",
        )

    # ── 2. RSS: inspects up to 8 entries per feed ────────────────────────────

    @patch("collectors.it_news.requests.get")
    @patch("collectors.it_news.feedparser.parse")
    def test_rss_inspects_up_to_eight_entries_per_feed(self, mock_parse, mock_get):
        """collect_rss_feeds must slice feed.entries[:8], not [:5]."""
        import feedparser
        from collectors.it_news import collect_rss_feeds

        def _make_entry(n):
            m = MagicMock()
            m.get.side_effect = lambda key, default="": {
                "title": f"Article {n}",
                "link": f"https://example.com/{n}",
                "summary": "summary",
                "published": "Mon, 21 Sep 2026 05:00:00 GMT",
            }.get(key, default)
            return m

        # Feed with 10 valid entries; collector must attempt at least 8 of them
        mock_feed = MagicMock()
        mock_feed.entries = [_make_entry(i) for i in range(10)]
        mock_parse.return_value = mock_feed
        mock_get.return_value.content = b"rss"

        # Patch Config to a single feed so we only count one feed's entries
        with patch("collectors.it_news.Config") as mock_cfg:
            mock_cfg.IT_NEWS_FEEDS = [{"name": "TestFeed", "url": "https://test.invalid/rss"}]
            articles = collect_rss_feeds()

        # With 10 valid entries and a slice of ≤8, we expect 8 articles (all have dates)
        self.assertGreaterEqual(
            len(articles),
            8,
            "collect_rss_feeds must inspect at least 8 entries per feed (currently slices at 5)",
        )

    # ── 3. HackerNews: inspects 20 story IDs ────────────────────────────────

    @patch("collectors.it_news.requests.get")
    def test_hackernews_inspects_twenty_story_ids(self, mock_get):
        """collect_hackernews must request 20 story IDs, not 10."""
        from collectors.it_news import collect_hackernews

        # Return 30 IDs; collector should request 20 individual items
        all_ids = list(range(1, 31))
        ids_response = MagicMock()
        ids_response.json.return_value = all_ids

        def _item_response(sid):
            r = MagicMock()
            r.json.return_value = {
                "id": sid,
                "title": f"Story {sid}",
                "url": f"https://hn-example.com/{sid}",
                "score": 10,
                "descendants": 5,
                "time": 1758488400,
            }
            return r

        mock_get.side_effect = [ids_response] + [_item_response(i) for i in range(1, 31)]

        articles = collect_hackernews()

        # Number of individual item calls = total get calls - 1 (the topstories call)
        individual_calls = mock_get.call_count - 1
        self.assertGreaterEqual(
            individual_calls,
            20,
            f"collect_hackernews must fetch 20 story items; only fetched {individual_calls}",
        )
        self.assertGreaterEqual(len(articles), 15)  # most should succeed

    # ── 4. Aggregate: ≤20 total, ≤5 per source, dynamic header ──────────────

    @patch("collectors.it_news.ArticleStore")
    @patch("collectors.it_news._get_now")
    @patch("collectors.it_news.collect_hackernews")
    @patch("collectors.it_news.collect_rss_feeds")
    def test_aggregate_caps_total_at_20_and_per_source_at_5(
        self, mock_rss, mock_hn, mock_now, mock_store_cls
    ):
        """collect_all_it_news must cap output: ≤20 total candidates, ≤5 per source.
        The header must reflect the actual candidate count dynamically."""
        from datetime import datetime, timezone, timedelta
        from collectors.it_news import collect_all_it_news

        now = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
        mock_now.return_value = now

        def _article(source, n, age_h=1):
            return {
                "source": source,
                "title": f"{source} Article {n}",
                "link": f"https://{source.lower()}.example.com/{n}",
                "summary": "summary",
                "published_at": now - timedelta(hours=age_h),
            }

        # 10 RSS articles from "FeedA", 10 from "FeedB", 15 HN articles → 35 total candidates
        mock_rss.return_value = (
            [_article("FeedA", i) for i in range(10)]
            + [_article("FeedB", i) for i in range(10)]
        )
        mock_hn.return_value = [_article("HackerNews", i) for i in range(15)]

        # Patch ArticleStore so no disk I/O; filter_fresh passes everything through
        store_instance = MagicMock()
        store_instance.has_seen.return_value = False
        mock_store_cls.return_value = store_instance

        with patch("collectors.it_news.filter_fresh") as mock_filter:
            # filter_fresh returns all articles unchanged (all fresh)
            all_in = mock_rss.return_value + mock_hn.return_value
            mock_filter.return_value = all_in

            result = collect_all_it_news()

        # Count how many articles appear in output (each has a numbered line "N. **Title**")
        import re
        article_lines = re.findall(r"^\d+\. \*\*", result, re.MULTILINE)
        total_in_output = len(article_lines)

        self.assertLessEqual(
            total_in_output,
            20,
            f"Output must contain ≤20 articles; found {total_in_output}",
        )

        # Per-source cap: count "FeedA" and "HackerNews" occurrences
        feeda_count = result.count("(FeedA)")
        feedb_count = result.count("(FeedB)")
        hn_count = result.count("(HackerNews)")
        self.assertLessEqual(feeda_count, 5, f"FeedA: {feeda_count} > 5")
        self.assertLessEqual(feedb_count, 5, f"FeedB: {feedb_count} > 5")
        self.assertLessEqual(hn_count, 5, f"HackerNews: {hn_count} > 5")

        # Dynamic header: the displayed number must match total_in_output
        self.assertIn(f"총 {total_in_output}건", result,
                      "Header must dynamically reflect the actual displayed article count")

    # ── 5. Resilience: malformed/failed feeds don't block others ─────────────

    @patch("collectors.it_news.requests.get")
    @patch("collectors.it_news.feedparser.parse")
    def test_malformed_feed_does_not_prevent_other_feeds(self, mock_parse, mock_get):
        """If one feed raises an exception, the others must still be collected."""
        from collectors.it_news import collect_rss_feeds

        good_entry = MagicMock()
        good_entry.get.side_effect = lambda key, default="": {
            "title": "Good Article",
            "link": "https://good.example.com/1",
            "summary": "summary",
            "published": "Mon, 21 Sep 2026 05:00:00 GMT",
        }.get(key, default)

        good_feed = MagicMock()
        good_feed.entries = [good_entry]

        # First feed raises, second feed returns one good article
        good_response = MagicMock(content=b"rss")
        mock_get.side_effect = [requests.RequestException("Network error"), good_response]
        mock_parse.return_value = good_feed

        with patch("collectors.it_news.Config") as mock_cfg:
            mock_cfg.IT_NEWS_FEEDS = [
                {"name": "BadFeed", "url": "https://bad.invalid/rss"},
                {"name": "GoodFeed", "url": "https://good.example.com/rss"},
            ]
            articles = collect_rss_feeds()

        self.assertEqual(1, len(articles), "Good feed article must be collected despite bad feed failure")
        self.assertEqual("Good Article", articles[0]["title"])
        self.assertEqual("GoodFeed", articles[0]["source"])

    @patch("collectors.it_news.requests.get")
    @patch("collectors.it_news.feedparser.parse")
    def test_rss_accepts_iso_updated_timestamp(self, mock_parse, mock_get):
        entry = {
            "title": "ISO dated article",
            "link": "https://example.com/iso",
            "summary": "summary",
            "updated": "2026-09-22T06:30:00Z",
        }
        mock_parse.return_value = SimpleNamespace(entries=[entry])
        mock_get.return_value.content = b"rss"

        with patch.object(
            __import__("collectors.it_news", fromlist=["Config"]).Config,
            "IT_NEWS_FEEDS",
            [{"name": "ISO Feed", "url": "https://example.com/feed"}],
        ):
            articles = __import__(
                "collectors.it_news", fromlist=["collect_rss_feeds"]
            ).collect_rss_feeds()

        self.assertEqual(1, len(articles))
        self.assertEqual(
            datetime(2026, 9, 22, 6, 30, tzinfo=timezone.utc),
            articles[0]["published_at"],
        )

    @patch("collectors.it_news.requests.get")
    @patch("collectors.it_news.feedparser.parse")
    def test_rss_fetch_uses_timeout_and_user_agent(self, mock_parse, mock_get):
        response = MagicMock(content=b"rss")
        mock_get.return_value = response
        mock_parse.return_value = SimpleNamespace(entries=[])

        with patch.object(
            __import__("collectors.it_news", fromlist=["Config"]).Config,
            "IT_NEWS_FEEDS",
            [{"name": "Timed Feed", "url": "https://example.com/feed"}],
        ):
            __import__(
                "collectors.it_news", fromlist=["collect_rss_feeds"]
            ).collect_rss_feeds()

        mock_get.assert_called_once_with(
            "https://example.com/feed",
            headers=unittest.mock.ANY,
            timeout=10,
        )
        response.raise_for_status.assert_called_once_with()
        mock_parse.assert_called_once_with(b"rss")

    @patch("collectors.it_news.ArticleStore")
    @patch("collectors.it_news._get_now")
    @patch("collectors.it_news.collect_hackernews", return_value=[])
    @patch("collectors.it_news.collect_rss_feeds")
    def test_aggregate_enforces_rolling_24_hour_window(
        self, mock_rss, _mock_hn, mock_now, mock_store_cls
    ):
        now = datetime(2026, 9, 23, 7, 0, tzinfo=timezone.utc)
        mock_now.return_value = now
        mock_store_cls.return_value.has_seen.return_value = False
        mock_rss.return_value = [
            {
                "source": "Feed",
                "title": "Fresh article",
                "link": "https://example.com/fresh",
                "summary": "fresh",
                "published_at": now - timedelta(hours=23),
            },
            {
                "source": "Feed",
                "title": "Stale article",
                "link": "https://example.com/stale",
                "summary": "stale",
                "published_at": now - timedelta(hours=25),
            },
        ]

        result = collect_all_it_news()

        self.assertIn("Fresh article", result)
        self.assertNotIn("Stale article", result)


if __name__ == "__main__":
    unittest.main()
