# Changelog

## 2026-07-14

### 수정
- `utils/time_utils.py`에 timezone-aware KST 현재 시각 및 브리핑 날짜 문자열 유틸리티 추가
- 브리핑 표시 날짜와 한국 주식 수집 기준 시각을 KST 기준으로 변경
- Open-Meteo 요청에 KST 오늘 날짜를 `start_date`와 `end_date`로 명시해 UTC 실행 환경의 날짜 불일치 방지
- UTC 15:00의 KST 날짜 전환과 UTC 자정 부근을 고정 시각으로 검증하고 Open-Meteo 요청 URL의 날짜 파라미터 확인
- `main.py`에서 더 이상 사용하지 않는 `datetime` import 제거

### 검증
- UTC 14:59:59/15:00:00 및 UTC 00:00:00의 UTC+9 날짜 계산 결과 확인
- 작업 환경에 Python 실행 파일이 없어 `python test_collectors.py` 회귀 테스트는 실행하지 못함

## 2026-06-13

### 변경 사항
- 멀티 AI 도구 통합설정 도입 (AGENTS.md / CLAUDE.md / handoff.md / CHANGELOG.md 생성)
- 그 이전 이력은 git 커밋 로그 참고
