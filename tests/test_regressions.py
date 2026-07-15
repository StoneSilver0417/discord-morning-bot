import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from collectors.civil_service import collect_all_civil_service
from collectors.it_news import collect_all_it_news
from collectors.weather import collect_wind_forecast
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

    @patch("collectors.it_news.collect_hackernews", return_value=[])
    @patch("collectors.it_news.collect_rss_feeds", return_value=[])
    def test_empty_it_news_is_failure(self, _rss, _hn):
        with self.assertRaises(RuntimeError):
            collect_all_it_news()

    @patch("collectors.civil_service.search_naver_news", return_value=[])
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
        "collectors.civil_service.search_naver_news",
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

    def test_empty_input_is_not_sent_to_gemini(self):
        with self.assertRaises(ValueError):
            process_with_gemini("it_news", "  ")

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.GenerativeModel")
    def test_gemini_failure_is_not_treated_as_success(self, mocked_model):
        mocked_model.return_value.generate_content.side_effect = RuntimeError("API failure")
        with self.assertRaises(RuntimeError):
            process_with_gemini("it_news", "뉴스 원문")

    @patch.object(main.Config, "GEMINI_API_KEY", "test-key")
    @patch("processors.gemini_processor.genai.GenerativeModel")
    def test_gemini_quota_exhaustion_returns_full_raw_news(self, mocked_model):
        raw_news = "뉴스 목록\n" + "A" * 5000
        mocked_model.return_value.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )

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


if __name__ == "__main__":
    unittest.main()
