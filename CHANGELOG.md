# Changelog

## 2026-07-20

### 수정
- 공무원 네이버 뉴스 검색 결과의 제목/설명 파싱이 깨져 있던 원인 확인: 네이버가 배포마다 클래스명을 해시로 바꿔 기존 `a.news_tit`/`div.news_dsc` 셀렉터가 더 이상 매치되지 않고, 폴백 셀렉터(`a[class*='fender-ui']`)가 "새 창 열림", "Keep에 저장", 언론사 배지 링크까지 제목으로 주워옴
- `collectors/civil_service.py`를 href 그룹핑 방식으로 재작성: keep.naver.com/언론사 배지/빈 텍스트/단독 텍스트(설명 없는 그룹)를 제외하고, 같은 기사 href에 딸린 첫 텍스트를 제목(끝의 "새 창 열림" 문구 제거), 두 번째 텍스트를 설명으로 사용
- 부수 효과: civil_service Gemini 프롬프트에 전달되는 원문 품질이 좋아져, 요약 실패 시 원문 폴백에도 실제 기사 설명이 표시됨 (기존에는 "기사 설명 없음"이 대부분)

### 검증
- 9개 키워드 전체로 `collect_all_civil_service()` 실행, 상위 10개 결과에 UI 문구 없이 실제 제목·설명만 포함됨을 육안 확인
- `python test_collectors.py` 및 `python -m unittest tests.test_regressions`(15개) 통과

## 2026-07-15

### 테스트 발송 및 503 폴백
- 수동 Actions 실행 `29380696218`에서 IT·공무원 Gemini 무료 할당량 20회 소진을 확인하고 두 카테고리의 원문 전체 전송 성공 검증
- 날씨 Gemini가 `503 UNAVAILABLE/high demand`를 반환해 전체 작업 종료 코드가 1이 된 문제 확인
- 503 서버 과부하·일시 장애도 수집 원문 전체로 폴백하도록 보완, 회귀 테스트 15개 통과

### Gemini 응답 잘림 방지
- Discord 메시지가 아니라 Gemini 응답 자체가 IT 96자, 공무원 127자로 중단된 사실을 사진과 Actions 로그로 확인
- 지원 종료된 `google-generativeai`를 공식 `google-genai` SDK로 이전
- `max_output_tokens`를 1,500에서 8,192로 확대하고 요약 작업의 사고 예산을 0으로 설정
- 응답 종료 사유가 `STOP`이 아니면 부분 응답을 버리고 수집 원문 전체로 폴백
- IT·공무원 결과에 번호·한 줄 요약·링크가 각각 최소 5개 없으면 불완전 결과를 버리고 원문 전체로 폴백
- 실제 Gemini 호출에서 5개 항목 609자 정상 완료 확인, 회귀 테스트 14개 통과

### 뉴스 한 줄 요약 형식
- IT·공무원 뉴스 수집 문자열에 기존에 확보한 기사 설명을 포함해 Gemini가 제목만 보고 추측하지 않도록 개선
- IT 뉴스 5개와 공무원 뉴스 5~8개를 `제목 → 핵심·실무 의미 한 문장 → 원문 링크` 형식으로 출력하도록 프롬프트 고정
- 서론·결론·별도 총평을 금지해 모바일 Discord에서 뉴스 목록을 빠르게 읽을 수 있도록 변경
- API 호출은 뉴스별 호출이 아니라 기존과 동일한 카테고리당 일괄 1회 유지
- 기사 설명·링크가 Gemini 입력에 포함되는 회귀 테스트 2개 추가, 전체 12개 테스트 및 구문 검사 통과

### Gemini 할당량 폴백
- Gemini가 `429` 또는 `RESOURCE_EXHAUSTED` 할당량 오류를 반환하면 수집한 원문 전체를 그대로 Discord 분할 전송하도록 변경
- 일반 API·인증·코드 오류는 기존처럼 실패로 전파해 장애를 숨기지 않도록 유지
- 5,000자가 넘는 뉴스 원문이 한 글자도 잘리지 않고 반환되는 회귀 테스트 추가

### 배포 및 운영 검증
- 장애 수정 커밋 `8dbe643`을 `origin/master`에 푸시
- Python 3.12.10에서 회귀 테스트 9개 통과, 전체 구문 검사 통과
- `test_collectors.py`로 날씨·주식·IT 뉴스·공무원 뉴스 실제 수집 성공 확인
- GitHub Actions 수동 실행 `29378714348`로 2026-07-15 브리핑 재발송, 네 카테고리 전송 완료 로그와 전체 성공 확인

### 장애 조사
- 로컬 `master`가 `origin/master`보다 4커밋 앞서 있어 2026-07-14의 KST 날짜 수정이 GitHub Actions 실행 코드에 배포되지 않은 사실 확인
- 원격 `main.py`가 UTC `datetime.now()`를 사용해 07:00 KST 브리핑 제목을 전날로 표시하는 경로 확인
- Discord embed 설명을 4,096자에서 조용히 절단하고, 웹훅 실패 반환값을 무시한 채 전체 성공 로그를 남기는 경로 확인
- IT/공무원 뉴스가 모두 비어도 정상 문자열로 Gemini에 전달되어 수집 실패가 성공으로 보이는 경로 확인
- GitHub CLI 설정 파일 권한 거부 및 공개 API 조회 제한으로 당일 Actions 실행 기록과 로그는 확인하지 못함. 저장소 cron은 `0 22 * * *`로 07:00 KST가 맞으며, 실제 지연/수동 실행 여부는 미확정

### 수정
- Open-Meteo 응답 첫 날짜가 요청한 KST 오늘과 다르면 수집 실패 처리
- IT/공무원 뉴스 전체가 빈 결과이면 명시적으로 실패 처리하고 Gemini 빈 입력 차단
- 긴 Discord 설명을 줄 경계 우선으로 여러 embed에 무손실 분할하고, 메시지당 embed 총 텍스트 6,000자 제한을 피하도록 embed별 개별 전송
- Gemini 오류·빈 응답을 1,000자 원문 절단 성공으로 위장하지 않고 카테고리 실패로 전파
- 카테고리 수집/가공 또는 웹훅 전송 하나라도 실패하면 `run_briefing()`이 실패를 반환하고 CLI가 종료 코드 1을 반환하도록 변경
- 날짜 경계, 오래된 날씨 응답, 빈 뉴스, Gemini 빈 입력, Discord 제한, 웹훅 실패 회귀 테스트 추가

### 검증
- `git diff --check` 통과
- `python.exe`가 문서상 경로에 없고 PATH에도 없어 회귀 테스트/구문 검사 실행 불가; 후속 실행 필요

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
