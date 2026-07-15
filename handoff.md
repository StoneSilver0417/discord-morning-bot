# 모닝브리핑 디스코드 봇 - Handoff

## 현재 상태

- **버전**: `master` 운영 중, 기준 커밋 `e842109` 이후 뉴스 한 줄 요약 형식 변경 작업 중
- **빌드/배포 상태**: 장애 수정과 Gemini 할당량 폴백은 `origin/master`에 배포 완료. 수동 재발송 Actions 실행 `29378714348` 성공
- **실행 방법**: 로컬 `python main.py`; GitHub Actions `Morning Briefing`은 매일 22:00 UTC(07:00 KST) 예약

## 최근 작업

1. Gemini가 `429/RESOURCE_EXHAUSTED`를 반환하면 실패하거나 내용을 자르지 않고 수집 원문 전체를 반환하도록 배포
2. IT·공무원 뉴스 수집 결과에 기사 설명을 포함하고, Gemini가 기사별 `제목 → 한 문장 요약 → 링크` 목록만 출력하도록 프롬프트 변경. 호출 횟수는 카테고리당 1회로 유지

## 알려진 이슈

- `google.generativeai` 패키지가 지원 종료되어 추후 `google.genai`로 이전 필요
- GitHub Actions가 사용하는 `actions/cache@v4`, `checkout@v4`, `setup-python@v5`의 Node.js 20 지원 종료 경고가 발생함
- 공무원 네이버 뉴스 크롤링 결과에 `새 창 열림`, `Keep에 저장` 같은 UI 문구가 제목으로 섞일 수 있음

## 다음 TODO

1. [ ] 뉴스 한 줄 요약 형식 변경 커밋·푸시
2. [ ] 다음 브리핑에서 한 줄 요약 형식과 할당량 소진 원문 폴백 확인
3. [ ] `google.generativeai`를 `google.genai`로 이전
