# 🤖 모닝브리핑 디스코드 봇

매일 아침 7시, 날씨/주식/IT뉴스/공무원 소식을 자동으로 디스코드에 전송하는 봇

## 기능

| 카테고리 | 내용 |
|----------|------|
| 🌤️ 날씨 | 경산 중방동 & 대구 만촌동 날씨, 옷차림, 미세먼지 |
| 📈 주식 | KOSPI/KOSDAQ/S&P500/나스닥 동향 + 증시 뉴스 |
| 💻 IT뉴스 | GeekNews, 요즘IT, HackerNews 등 큐레이션 |
| 🏛️ 공무원 | 전산직/사회복지직 관련 뉴스 |

모든 정보는 **Google Gemini AI**로 요약/가공되어 전송됩니다.

## 설정 방법

### 1. API 키 준비

| 서비스 | 발급 방법 |
|--------|-----------|
| Discord Webhook URL | 서버 설정 → 연동 → 웹훅 → 새 웹훅 → URL 복사 |
| Google Gemini API Key | https://aistudio.google.com 가입 후 API 키 발급 |

### 2. 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 실행
python main.py
```

### 3. GitHub Actions 배포 (자동 실행)

1. 이 레포를 GitHub에 Push
2. GitHub 레포 → **Settings** → **Secrets and variables** → **Actions**
3. 다음 시크릿 추가:
   - `DISCORD_WEBHOOK_MAIN`: Discord Webhook URL
   - `GEMINI_API_KEY`: Gemini API 키
4. 매일 KST 07:00에 자동 실행됨
5. **Actions** 탭에서 `workflow_dispatch`로 수동 테스트 가능

## 기술 스택

- Python 3.12
- GitHub Actions (무료 cron)
- Discord Webhook (봇 토큰 불필요)
- Google Gemini Flash (무료 LLM)
- 네이버 날씨/증권 크롤링
- Open-Meteo API (바람/기압)
- yfinance + FinanceDataReader (주식)
- RSS/Hacker News API (IT 뉴스)
