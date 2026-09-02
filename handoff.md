# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중 (`origin/master` 최신 커밋 배포 완료)
- **빌드/배포 상태**: 수동 실행 `33585561823`(2026-09-02)에서 4개 카테고리(날씨, 주식, IT뉴스, 공무원) 전부 Gemini 가공 성공 + Discord 전송 성공(`success`) 확인
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. IT뉴스 및 공무원 뉴스 Gemini 요약 실패 및 원문 전송 이슈 수정 (2026-09-02):
   - Pro 모델의 429 할당량 오류 방지를 위해 모든 카테고리 기본 모델을 `gemini-3.6-flash`로 통일
   - 429, 404, 503 오류 발생 시 `fallback_model`로 1회 즉시 재시도하도록 `processors/gemini_processor.py` 개선
   - 3~5개 선별 및 심층 요약 프롬프트와 회귀 테스트 39개 검증 완료
   - GitHub Actions 워크플로우 실행(`33585561823`)에서 4개 카테고리 모두 Gemini 요약 및 Discord 전송 성공 확인
2. 공무원 네이버 뉴스 수집기의 제목/설명 셀렉터가 네이버 마크업 변경으로 깨져 "새 창 열림" 등 UI 문구가 섞이던 문제 수정 (2026-07-20, 커밋 `7155233`, 상세는 CHANGELOG 참고)

## 알려진 이슈

- `requirements.txt`의 `google-genai>=1.0.0`이 상한 없이 열려 있어, Google이 모델 별칭이나 파라미터 제약을 다시 바꾸면 이번과 같은 장애가 재발할 수 있음 (사용자 확인 후 현재는 버전 고정하지 않기로 결정)
- `test_collectors.py`는 외부 서비스 응답 오류를 출력만 하고 종료 코드를 실패로 반환하지 않아 자동 회귀 판정에는 한계가 있음
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함

## 다음 TODO

1. [ ] 다음 스케줄 실행(익일 07:00 KST)이 정상 성공하는지 확인
