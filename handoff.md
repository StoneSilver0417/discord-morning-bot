# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중, 기준 커밋 `213dfa7` 이후 Gemini 응답 잘림 방지 작업 중
- **빌드/배포 상태**: 뉴스 한 줄 요약 형식까지 `origin/master`에 배포 완료. 수동 실행 `29380181820`에서 짧은 AI 응답 재현
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. 사진과 Actions 로그로 Discord 제한이 아니라 Gemini의 1,500 출력 토큰·사고 토큰 소비 때문에 IT 96자, 공무원 127자로 응답이 중단된 사실 확인
2. 공식 `google-genai` SDK로 이전하고 출력 예산 8,192, 사고 예산 0 적용. 비정상 종료 또는 뉴스 5개 미만이면 잘린 AI 응답 대신 원문 전체를 전송하도록 변경

## 알려진 이슈

- `google.generativeai` 패키지가 지원 종료되어 추후 `google.genai`로 이전 필요
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함
- 공무원 네이버 뉴스 크롤링 결과에 `새 창 열림`, `Keep에 저장` 같은 UI 문구가 제목으로 섞일 수 있음

## 다음 TODO

1. [ ] Gemini 잘림 방지 및 SDK 이전 변경 커밋·푸시
2. [ ] 수동 브리핑으로 IT·공무원 뉴스가 최소 5개씩 끝까지 전송되는지 확인
3. [ ] 공무원 네이버 검색 결과의 UI 문구 제목 필터링 개선
