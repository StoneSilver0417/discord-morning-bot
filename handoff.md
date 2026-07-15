# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중, 기준 커밋 `8dbe643` 이후 Gemini 할당량 폴백 변경 작업 중
- **빌드/배포 상태**: 2026-07-15 장애 수정은 `origin/master`에 배포 완료. 수동 재발송 Actions 실행 `29378714348` 성공
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. KST 날짜 검증, 빈 뉴스·웹훅 실패 감지, Discord 장문 무손실 분할을 배포하고 회귀 테스트 9개 및 실제 수집기 4종 통과 후 오늘 브리핑 재발송 완료
2. Gemini가 `429/RESOURCE_EXHAUSTED`를 반환하면 실패하거나 내용을 자르지 않고 수집 원문 전체를 반환하도록 변경하고 5,000자 원문 보존 테스트 추가

## 알려진 이슈

- `google.generativeai` 패키지가 지원 종료되어 추후 `google.genai`로 이전 필요
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함
- 공무원 네이버 뉴스 크롤링 결과에 `새 창 열림`, `Keep에 저장` 같은 UI 문구가 제목으로 섞일 수 있음

## 다음 TODO

1. [ ] Gemini 할당량 폴백 변경 커밋·푸시
2. [ ] 다음 예약 브리핑에서 할당량 소진 시 원문 목록이 여러 Discord 메시지로 온전히 전송되는지 확인
3. [ ] `google.generativeai`를 `google.genai`로 이전
