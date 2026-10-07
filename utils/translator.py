"""번역 및 한글화 유틸리티 모듈

해외 IT 뉴스(TechCrunch, Wired, The Verge, Ars Technica, HackerNews 등)의
영문 제목 및 요약을 한국어로 번역 및 현지화합니다.
"""
import html
import json
import re
import urllib.parse
import urllib.request
from utils.logger import setup_logger

logger = setup_logger("translator")
_TRANSLATION_CACHE: dict[str, str | None] = {}


def is_primarily_english(text: str) -> bool:
    """텍스트가 주로 영문으로 구성되어 있는지 확인합니다."""
    if not text or not isinstance(text, str):
        return False
    clean = text.strip()
    if not clean:
        return False
    has_hangul = bool(re.search(r"[\uac00-\ud7a3]", clean))
    has_latin = bool(re.search(r"[a-zA-Z]", clean))
    if not has_latin:
        return False
    if not has_hangul:
        return True
    # 한글과 영문이 혼용된 경우, 영문 글자 수가 한글 글자 수의 3배를 초과하면 영문으로 판단
    hangul_count = len(re.findall(r"[\uac00-\ud7a3]", clean))
    latin_count = len(re.findall(r"[a-zA-Z]", clean))
    return latin_count > (hangul_count * 3)


def translate_en_to_ko(text: str, timeout: int = 5) -> str | None:
    """영문 텍스트를 무료 번역 API를 통해 한국어로 번역합니다.

    실패 시 None을 반환하며, 외부 예외는 발생시키지 않습니다.
    """
    if not text or not isinstance(text, str):
        return None
    clean_text = text.strip()
    if not clean_text:
        return None
    if not is_primarily_english(clean_text):
        return clean_text

    if clean_text in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[clean_text]

    try:
        encoded_text = urllib.parse.quote(clean_text[:500])
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=en|ko"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = data.get("responseData", {}).get("translatedText", "").strip()
            if translated and bool(re.search(r"[\uac00-\ud7a3]", translated)):
                res = html.unescape(translated)
                _TRANSLATION_CACHE[clean_text] = res
                return res
    except Exception as e:
        logger.debug(f"번역 실패 ('{clean_text[:30]}...'): {e}")

    _TRANSLATION_CACHE[clean_text] = None
    return None


def translate_article_title(title: str) -> str:
    """기사 제목이 영문인 경우 한국어로 번역합니다.

    번역 실패 시 원문 제목을 반환합니다.
    """
    if not title or not is_primarily_english(title):
        return title
    translated = translate_en_to_ko(title)
    if translated and translated.strip():
        return translated.strip()
    return title


def translate_article_summary(summary: str, fallback_prompt: bool = True) -> str:
    """기사 요약이 영문인 경우 한국어로 번역합니다.

    번역 실패 시 기본 한글 안내 문구로 대체합니다.
    """
    if not summary or not summary.strip():
        return "기사 설명 없음"
    if not is_primarily_english(summary):
        return summary.strip()
    translated = translate_en_to_ko(summary)
    if translated and translated.strip():
        return translated.strip()
    if fallback_prompt:
        return "해외 IT 기사 원문입니다. (상세 내용은 원문 링크 참고)"
    return summary.strip()


def localize_news_body(body: str) -> str:
    """뉴스 마크다운 본문 내의 영문 제목 및 설명을 한국어로 변환합니다."""
    if not body or not is_primarily_english(body):
        return body

    lines = body.strip().splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # 제목 라인 확인: **Title** (Source) 또는 **Title**
        bold_match = re.match(r"^(\s*\*\*)([^*]+)(\*\*\s*(?:\([^)]+\))?\s*)$", line)
        if bold_match:
            prefix, title_content, suffix = bold_match.groups()
            if is_primarily_english(title_content):
                tr_title = translate_article_title(title_content)
                new_lines.append(f"{prefix}{tr_title}{suffix}")
            else:
                new_lines.append(line)
            continue

        # 설명 라인 확인: 설명: ...
        summary_match = re.match(r"^(\s*설명:\s*)(.*)$", line)
        if summary_match:
            prefix, summary_content = summary_match.groups()
            if is_primarily_english(summary_content):
                tr_summary = translate_article_summary(summary_content)
                new_lines.append(f"{prefix}{tr_summary}")
            else:
                new_lines.append(line)
            continue

        new_lines.append(line)

    return "\n".join(new_lines)
