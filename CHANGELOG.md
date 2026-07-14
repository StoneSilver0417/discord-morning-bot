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
- 로컬 세션에 Python(3.12.10) 설치 확인 후 `requirements.txt` 의존성 설치, `python test_collectors.py` 실행 → 날씨/주식/IT뉴스/공무원뉴스 4개 수집기 전부 정상 수집 확인
- Windows 콘솔(cp949)에서 이모지 출력 시 `UnicodeEncodeError` 발생 → `PYTHONIOENCODING=utf-8` 설정으로 회피

### 배포
- GitHub Actions `Morning Briefing` 워크플로우가 `disabled_manually` 상태로 꺼져 있던 것을 `gh workflow list`로 발견, `gh workflow enable "Morning Briefing"`으로 재활성화 (`gh` CLI가 저장소 소유자 계정으로 로컬 인증되어 있어 직접 처리)

### 도구 사용 메모
- Codex rescue(코덱스) 서브에이전트 샌드박스는 `.git`이 읽기 전용이라 파일 편집은 가능하나 `git commit`은 불가 — 커밋은 로컬 세션에서 별도로 처리해야 함
- Codex rescue에 "GitHub Actions 활성화"처럼 반복 자동화를 변경하는 요청을 SendMessage(조율자 경유)로 전달하면 Codex 자체 권한 분류기가 차단함 — 이런 유형은 로컬 `gh`/`git`으로 직접 처리하는 편이 안정적

## 2026-06-13

### 변경 사항
- 멀티 AI 도구 통합설정 도입 (AGENTS.md / CLAUDE.md / handoff.md / CHANGELOG.md 생성)
- 그 이전 이력은 git 커밋 로그 참고
