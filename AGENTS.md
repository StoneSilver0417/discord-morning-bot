# 모닝브리핑 디스코드 봇 — 프로젝트 규칙

> 베이스 규칙: `D:\workspace\AGENTS.md`를 먼저 읽고 따른다. (자동 로드되지 않은 경우 직접 읽을 것)
> 현재 진행 상태·TODO는 `handoff.md`, 과거 이력은 `CHANGELOG.md` 참고.

## 개요
- 매일 아침 7시 날씨(경산 중방동·대구 만촌동)/주식/IT뉴스/공무원 소식을 디스코드 웹훅으로 전송하는 봇
- 모든 정보는 Google Gemini AI로 요약·가공

## 기술 스택
- Python (collectors / processors / formatters / utils 모듈 구조, 진입점 `main.py`)
- Google Gemini API (요약), Discord Webhook (전송)
- 스케줄링: GitHub Actions (`.github/workflows/morning_briefing.yml`)

## 주요 명령어
```bash
pip install -r requirements.txt   # 의존성 설치
python main.py                    # 로컬 실행 (브리핑 1회 전송)
python test_collectors.py         # 수집기 테스트
```

## 환경
- API 키: `.env` (로컬) — `DISCORD_WEBHOOK_URL`, Gemini API 키 (`.env.example` 참고)
- GitHub Actions에서는 저장소 Secrets 사용
