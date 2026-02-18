# Meemoo — Telegram Memo Bot

URL 또는 텍스트를 보내면 자동으로 분석하여 제목, 요약(3줄), 카테고리, 태그를 생성하고 Supabase에 저장합니다.

## 파이프라인

```
🎯 Router → 🔍 Analyst → 📚 Librarian → 💡 Recommender(명시적 요청 시만)
```

- **Router**: 규칙 기반, LLM 불필요
- **Analyst**: Claude로 제목/요약/카테고리/태그 JSON 생성
- **Librarian**: Supabase 저장·중복 감지·검색·목록·삭제
- **Recommender**: 메타데이터 기반 재랭크 (명시 요청 시만)

## 케미담당 (💖 Banter)

URL 저장 후 캐릭터 3인이 한 줄 코멘트를 랜덤으로 남깁니다.

| 캐릭터 | 성격 |
|--------|------|
| 팀장 | 장난기 있고 여유로운 자신감, 가벼운 티징 |
| 분석가 | 건조한 관찰자, 논리적 프레임의 드라이한 위트 |
| 사서 | 조용하고 문학적, 분위기·사물·어휘 중심 |

## 스케줄러

| 시각 (KST) | 내용 |
|-----------|------|
| 매일 06:00 | 🧃 날씨 + 날짜 포함 아침 인사 (캐릭터 랜덤) |
| 매일 09:00 | 💡 저장된 메모 기반 추천 |
| 매일 20:00 | 💡 저장된 메모 기반 추천 |

날씨는 `wttr.in` (마포구, 서울) 기준이며 API 키 불필요.

## 환경 변수

```bash
# 필수
TELEGRAM_TOKEN=       # BotFather 토큰
ANTHROPIC_API_KEY=    # Claude API 키
SUPABASE_URL=         # Supabase 프로젝트 URL
SUPABASE_ANON_KEY=    # Supabase anon 키

# 선택
VERBOSE_DEFAULT=0     # 1이면 기본 verbose 모드
CLAUDE_MODEL=claude-sonnet-4-5-20250929
MAX_EXTRACT_CHARS=4000
```

## 설치 & 실행

```bash
pip install -r requirements.txt
python -m app.main
```

## DB 마이그레이션

Supabase SQL Editor에서 `supabase/migrations/001_create_memos.sql` 실행.

## 명령어

| 명령 | 설명 |
|------|------|
| URL 전송 | 자동 분석 & 저장 |
| 텍스트 전송 (10자 초과) | 텍스트 메모 저장 |
| `/save <URL>` | 분석 & 저장 |
| `/list` | 메모 목록 (페이지네이션) |
| `/search <키워드>` | 키워드 검색 (페이지네이션) |
| `/category` | 카테고리 목록 |
| `/category <이름>` | 카테고리별 메모 목록 |
| `/view <id>` | 메모 상세 보기 |
| `/delete <id>` | 삭제 |
| `/recommend` | 추천 (Claude 호출) |
| `/sms` | 🧃 캐릭터 한 줄 인사 |
| `/verbose on\|off` | 단계별 메시지 표시 토글 |
| `/help` | 사용법 |
| `/start` | 봇 시작 & 사용자 등록 |

## 예시 Telegram 흐름

### 기본 모드 (URL 전송)
```
User: https://example.com/article

Bot: 🔍 분석가: 핵심 정리 중...

Bot: 📚 저장 완료!
     `AI 기술 동향 2026`

Bot: ✏️ 분석가: 오, 이건 좀 쌓아둘 만한데.

Bot: 📌 AI 기술 동향 2026
       • 2026년 주요 AI 트렌드 요약
       • 멀티모달 에이전트의 부상
       • 오픈소스 모델 경쟁 심화
     📂 기술  🏷 #AI #트렌드
```

### Verbose 모드
```
User: /verbose on
Bot: 🔧 Verbose 모드: `ON`

User: https://example.com/article

Bot: 🔧 [🔍 Analyst]
     {"title":"AI 기술 동향 2026","bullets":[...],"category":"기술","tags":["AI"]}

Bot: 📌 AI 기술 동향 2026 ...

Bot: 🔧 [📚 Librarian]
     {"action":"saved","memo":{...}}

Bot: 📚 저장 완료!
     `AI 기술 동향 2026`
```

### 스케줄 메시지
```
Bot: 🧃 팀장: 마포구 맑음 12도, 오늘은 뭐 저장하지?

Bot: 💡 큐레이터 추천
     📌 AI 기술 동향 2026  (기술)
     ...
```

## 아키텍처

```
app/
├── main.py          # Telegram bot 진입점, 핸들러
├── router.py        # 규칙 기반 라우터
├── workers.py       # Analyst / Librarian / Recommender 실행
├── claude_client.py # Claude API 호출
├── supabase_client.py # DB 읽기·쓰기
├── extractor.py     # URL 콘텐츠 추출
├── formatter.py     # Telegram 메시지 포맷
├── banter.py        # 케미담당 한 줄 코멘트
├── scheduler.py     # APScheduler 크론 잡
├── schemas.py       # JSON 스키마 & 라우터 명령 맵
└── config.py        # 환경 변수 로드
supabase/
└── migrations/
    └── 001_create_memos.sql
```
