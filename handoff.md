# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중, 기준 커밋 `beaa016` 이후 Gemini 503 폴백 보완 작업 중
- **빌드/배포 상태**: Gemini 잘림 방지까지 `origin/master`에 배포 완료. 수동 실행 `29380696218`에서 IT·공무원 원문 폴백 전송 성공, 날씨 503으로 작업 종료 코드는 실패
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. 공무원 네이버 뉴스 수집기의 제목/설명 셀렉터(`a.news_tit`, `div.news_dsc`)가 네이버 마크업 변경으로 깨져 "새 창 열림"·"Keep에 저장"·언론사 배지가 제목으로 섞이고 설명은 항상 비던 문제 수정. 실제 기사 링크만 href로 그룹핑해 제목/설명을 추출하도록 재작성, 회귀 테스트 15개 통과 (2026-07-20, 커밋 `7155233`)
2. Gemini 응답 잘림·503 장애·할당량 소진에 각각 원문 전체 폴백을 적용하고 `google-genai` 공식 SDK로 이전 완료 (2026-07-15, 상세는 CHANGELOG 참고)

## 알려진 이슈

- `test_collectors.py`는 외부 서비스 응답 오류를 출력만 하고 종료 코드를 실패로 반환하지 않아 자동 회귀 판정에는 한계가 있음
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함

## 다음 TODO

1. [ ] Gemini 503 일시 장애 폴백 변경 커밋·푸시
2. [ ] 다음 예약 실행의 전체 성공 여부 확인
