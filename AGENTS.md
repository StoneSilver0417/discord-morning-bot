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
- 로컬 Windows 세션에 Python 3.12(`C:\Users\PC\AppData\Local\Programs\Python\Python312`)가 설치되어 있음. `requirements.txt` 의존성은 미설치 상태일 수 있으니 `python -m pip install -r requirements.txt` 먼저 실행
- Windows 콘솔(cp949)에서 이모지가 포함된 스크립트(`test_collectors.py` 등) 실행 시 `UnicodeEncodeError`가 날 수 있음 — `PYTHONIOENCODING=utf-8` 설정 후 실행
- GitHub 저장소: `StoneSilver0417/discord-morning-bot`, 워크플로우명 `Morning Briefing`(`.github/workflows/morning_briefing.yml`). 로컬에 `gh` CLI가 저장소 소유자 계정으로 인증되어 있어 `gh workflow list/enable` 등 직접 사용 가능
- Codex rescue(코덱스) 서브에이전트 샌드박스는 `.git` 쓰기가 막혀 있고, GitHub Actions 활성화처럼 반복 자동화를 바꾸는 요청은 조율자 경유(SendMessage)로 보내면 Codex 자체 분류기가 차단할 수 있음 — 이런 작업은 로컬 세션에서 `git`/`gh`로 직접 처리할 것
