# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중 (`origin/master` 최신 커밋 `e472094`까지 배포 완료)
- **빌드/배포 상태**: 수동 실행 `29990930845`(2026-07-23)에서 4개 카테고리 전부 Gemini 가공 성공 + Discord 전송 성공(`success`) 확인
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. 2026-07-21~22 스케줄 실행이 이틀 연속 4개 카테고리 전부 `400 INVALID_ARGUMENT`로 실패한 원인 확인: `google-genai` SDK가 2.12.1→2.13.0으로 자동 업그레이드되며 `gemini-flash-latest` 별칭이 `gemini-3.6-flash`로 바뀌었고, 이 모델은 `thinking_budget=0`(사고 완전 비활성화)을 더 이상 허용하지 않음. `thinking_budget=1`로 수정, 회귀 테스트 15개 + 실제 API 호출 + 수동 워크플로우 실행으로 정상화 확인 (2026-07-23, 커밋 `e472094`)
2. 공무원 네이버 뉴스 수집기의 제목/설명 셀렉터가 네이버 마크업 변경으로 깨져 "새 창 열림" 등 UI 문구가 섞이던 문제 수정 (2026-07-20, 커밋 `7155233`, 상세는 CHANGELOG 참고)

## 알려진 이슈

- `requirements.txt`의 `google-genai>=1.0.0`이 상한 없이 열려 있어, Google이 모델 별칭이나 파라미터 제약을 다시 바꾸면 이번과 같은 장애가 재발할 수 있음 (사용자 확인 후 현재는 버전 고정하지 않기로 결정)
- `test_collectors.py`는 외부 서비스 응답 오류를 출력만 하고 종료 코드를 실패로 반환하지 않아 자동 회귀 판정에는 한계가 있음
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함

## 다음 TODO

1. [ ] 다음 스케줄 실행(익일 07:00 KST)이 정상 성공하는지 확인
