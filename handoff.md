# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: 운영 중 (GitHub Actions 매일 아침 7시 자동 실행)
- **빌드/배포 상태**: GitHub Actions `morning_briefing.yml` (워크플로우명 `Morning Briefing`) — `active` 상태 (2026-07-14 재활성화)
- **실행 방법**: 로컬은 `python main.py` (`.env` 필요)

## 최근 작업

1. GitHub Actions의 UTC 시스템 시간과 무관하게 브리핑 날짜·주식 기준 시각·Open-Meteo 조회 날짜를 KST로 계산하도록 수정, 로컬에 Python/의존성 설치 후 `test_collectors.py`로 4개 수집기(날씨/주식/IT뉴스/공무원뉴스) 전량 통과 검증함 (2026-07-14, 커밋 c8c2dcf)
2. `Morning Briefing` 워크플로우가 `disabled_manually` 상태였던 것을 발견해 `gh workflow enable`로 재활성화함 (2026-07-14)

## 알려진 이슈

- `test_collectors.py`는 외부 서비스 응답 오류를 출력만 하고 종료 코드를 실패로 반환하지 않아 자동 회귀 판정에는 한계가 있음

## 다음 TODO

1. [ ] 날짜 경계 검증을 자동화된 단위 테스트로 편입
2. [ ] 수집기 테스트가 수집 실패 시 비정상 종료하도록 개선
