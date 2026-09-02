import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
        raw_news = "뉴스 목록\n" + "A" * 5000
        mocked_client.return_value.models.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )

        self.assertEqual(raw_news, process_with_gemini("it_news", raw_news))

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
        raw_news = "완전한 원문 뉴스 목록"
        response = Mock()
        response.text = "중간에 잘린 AI 응답"
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        self.assertEqual(raw_news, process_with_gemini("it_news", raw_news))

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_short_news_list_returns_full_raw_news(self, mocked_client):
        raw_news = "완전한 원문 뉴스 목록"
        response = Mock()
        response.text = "1. 첫 기사\n→ 한 줄 요약\n🔗 https://example.com/1"
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        self.assertEqual(raw_news, process_with_gemini("it_news", raw_news))

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
            model="gemini-2.0-flash",
            contents=unittest.mock.ANY,
            config=unittest.mock.ANY,
        )

        mocked_client.return_value.models.generate_content.reset_mock()
        response.text = (
            "1. 기사1\n→ 요약1\n🔗 https://example.com/1\n"
            "2. 기사2\n→ 요약2\n🔗 https://example.com/2\n"
            "3. 기사3\n→ 요약3\n🔗 https://example.com/3"
        )
        process_with_gemini("it_news", "IT뉴스 원문")
        mocked_client.return_value.models.generate_content.assert_called_with(
            model="gemini-2.5-pro",
            contents=unittest.mock.ANY,
            config=unittest.mock.ANY,
        )

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_gemini_fallback_on_404(self, mocked_client):
        response = Mock()
        response.text = (
            "1. 기사1\n→ 요약1\n🔗 https://example.com/1\n"
            "2. 기사2\n→ 요약2\n🔗 https://example.com/2\n"
            "3. 기사3\n→ 요약3\n🔗 https://example.com/3"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.side_effect = [
            RuntimeError("404 Not Found: models/gemini-2.5-pro is not found"),
            response,
        ]

        result = process_with_gemini("it_news", "IT뉴스 원문")
        self.assertIn("1. 기사1", result)
        self.assertEqual(2, mocked_client.return_value.models.generate_content.call_count)
        first_call = mocked_client.return_value.models.generate_content.call_args_list[0]
        second_call = mocked_client.return_value.models.generate_content.call_args_list[1]
        self.assertEqual("gemini-2.5-pro", first_call.kwargs["model"])
        self.assertEqual("gemini-2.0-flash", second_call.kwargs["model"])

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_news_list_minimum_three_accepted(self, mocked_client):
        raw_news = "완전한 원문 뉴스 목록"
        response = Mock()
        response.text = (
            "1. 기사1\n→ 요약1\n🔗 https://example.com/1\n"
            "2. 기사2\n→ 요약2\n🔗 https://example.com/2\n"
            "3. 기사3\n→ 요약3\n🔗 https://example.com/3"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(response.text, result)

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.Client")
    def test_news_list_two_items_rejected(self, mocked_client):
        raw_news = "완전한 원문 뉴스 목록"
        response = Mock()
        response.text = (
            "1. 기사1\n→ 요약1\n🔗 https://example.com/1\n"
            "2. 기사2\n→ 요약2\n🔗 https://example.com/2"
        )
        response.candidates = [
            SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))
        ]
        mocked_client.return_value.models.generate_content.return_value = response

        result = process_with_gemini("it_news", raw_news)
        self.assertEqual(raw_news, result)

    def test_system_prompts_selective_3_to_8(self):
        from processors.gemini_processor import SYSTEM_PROMPTS
        self.assertIn("3~8개", SYSTEM_PROMPTS["it_news"])
        self.assertIn("전산직 공무원", SYSTEM_PROMPTS["it_news"])
        self.assertIn("3~8개", SYSTEM_PROMPTS["civil_service"])
        self.assertIn("[전산직] [복지직] [공통]", SYSTEM_PROMPTS["civil_service"])

    def test_is_model_not_found_detection(self):
        from processors.gemini_processor import _is_model_not_found
        self.assertTrue(_is_model_not_found(RuntimeError("404 Not Found: model is not found")))
        self.assertTrue(_is_model_not_found(Exception("models/gemini-2.5-pro is not supported")))
        self.assertFalse(_is_model_not_found(RuntimeError("500 Internal Server Error")))

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
            self.assertEqual("gemini-2.0-flash", cfg.GEMINI_MODEL_WEATHER)
            self.assertEqual("gemini-2.0-flash", cfg.GEMINI_MODEL_STOCKS)
            self.assertEqual("gemini-2.5-pro", cfg.GEMINI_MODEL_IT_NEWS)
            self.assertEqual("gemini-2.5-pro", cfg.GEMINI_MODEL_CIVIL_SERVICE)
            self.assertEqual("gemini-2.0-flash", cfg.GEMINI_MODEL_FALLBACK)
            self.assertEqual("gemini-2.0-flash", cfg.get_model_for_category("weather"))
            self.assertEqual("gemini-2.0-flash", cfg.get_model_for_category("stocks"))
            self.assertEqual("gemini-2.5-pro", cfg.get_model_for_category("it_news"))
            self.assertEqual("gemini-2.5-pro", cfg.get_model_for_category("civil_service"))

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


if __name__ == "__main__":
    unittest.main()
