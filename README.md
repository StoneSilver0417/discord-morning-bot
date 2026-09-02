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

> 💡 뉴스 및 증시 수집은 Google News RSS 및 무료 피드를 사용하므로 별도의 포털/검색 API 키가 필요하지 않습니다.

### 2. 환경변수 및 모델 커스텀 설정

`.env` 파일(로컬) 또는 GitHub Secrets에 다음 설정을 구성할 수 있습니다.

#### 필수 환경변수
- `DISCORD_WEBHOOK_MAIN`: Discord Webhook URL (단일 채널 전송 시) 또는 카테고리별 웹훅 URL (`DISCORD_WEBHOOK_WEATHER`, `DISCORD_WEBHOOK_STOCKS`, `DISCORD_WEBHOOK_IT_NEWS`, `DISCORD_WEBHOOK_CIVIL_SERVICE`)
- `GEMINI_API_KEY`: Google Gemini API 키

#### 카테고리별 Gemini 모델 커스텀 (선택)
카테고리별로 원하는 Gemini 모델을 환경변수로 지정할 수 있으며, 미지정 시 기본 모델이 적용됩니다.

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `GEMINI_MODEL_WEATHER` | `gemini-3.6-flash` | 날씨 브리핑 요약 모델 |
| `GEMINI_MODEL_STOCKS` | `gemini-3.6-flash` | 주식/증시 동향 요약 모델 |
| `GEMINI_MODEL_IT_NEWS` | `gemini-3.6-flash` | IT 뉴스 큐레이션 및 요약 모델 |
| `GEMINI_MODEL_CIVIL_SERVICE` | `gemini-3.6-flash` | 공무원 뉴스 큐레이션 및 요약 모델 |
| `GEMINI_MODEL_FALLBACK` | `gemini-3.6-flash` | 모델 호출 실패 시 대체(Fallback) 모델 |

### 3. 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env 파일을 열어 API 키 및 설정 입력

# 실행
python main.py
```

### 4. GitHub Actions 배포 (자동 실행)

1. 이 레포를 GitHub에 Push
2. GitHub 레포 → **Settings** → **Secrets and variables** → **Actions**
3. 다음 Secrets 추가:
   - **필수**:
     - `DISCORD_WEBHOOK_MAIN` (또는 카테고리별 `DISCORD_WEBHOOK_*`)
     - `GEMINI_API_KEY`
   - **선택 (모델 커스텀)**:
     - `GEMINI_MODEL_WEATHER`, `GEMINI_MODEL_STOCKS`, `GEMINI_MODEL_IT_NEWS`, `GEMINI_MODEL_CIVIL_SERVICE`
4. 매일 KST 07:00에 자동 실행됨
5. **Actions** 탭에서 `workflow_dispatch`로 수동 테스트 가능

## 기술 스택

- Python 3.12
- GitHub Actions (무료 cron)
- Discord Webhook (봇 토큰 불필요)
- Google Gemini API (`gemini-3.6-flash`)
- Open-Meteo API (날씨 예보 및 미세먼지 대기질)
- Google News RSS (증시 시황 및 공무원 뉴스 검색, API 키 불필요)
- yfinance + FinanceDataReader (주식 지수 및 시세)
- RSS Feed (GeekNews, 요즘IT, TechCrunch, 44bits 등 IT 뉴스)
