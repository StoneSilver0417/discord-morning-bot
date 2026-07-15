# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중, 기준 커밋 `beaa016` 이후 Gemini 503 폴백 보완 작업 중
- **빌드/배포 상태**: Gemini 잘림 방지까지 `origin/master`에 배포 완료. 수동 실행 `29380696218`에서 IT·공무원 원문 폴백 전송 성공, 날씨 503으로 작업 종료 코드는 실패
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. 공식 `google-genai` SDK로 이전하고 출력 예산 8,192, 사고 예산 0 적용. 비정상 종료 또는 뉴스 5개 미만이면 원문 전체를 전송하도록 배포
2. 테스트 발송에서 무료 할당량 20회 소진 시 IT·공무원 원문 폴백과 전송 성공 확인. 날씨 Gemini의 503 고수요 오류도 수집 원문으로 폴백하도록 추가

## 알려진 이슈

- `google.generativeai` 패키지가 지원 종료되어 추후 `google.genai`로 이전 필요
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함
- 공무원 네이버 뉴스 크롤링 결과에 `새 창 열림`, `Keep에 저장` 같은 UI 문구가 제목으로 섞일 수 있음

## 다음 TODO

1. [ ] Gemini 503 일시 장애 폴백 변경 커밋·푸시
2. [ ] 다음 예약 실행의 전체 성공 여부 확인
3. [ ] 공무원 네이버 검색 결과의 UI 문구 제목 필터링 개선
