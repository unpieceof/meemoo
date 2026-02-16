# Meemoo — Telegram Memo Bot

URL을 보내면 자동으로 분석하여 제목, 요약(3줄), 카테고리, 태그를 생성하고 Supabase에 저장합니다.

## 파이프라인

```
🎯 Router → 🔍 Analyst → 📚 Librarian → 💡 Recommender(요청 시만)
```

## 환경 변수

```bash
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
| `/save <URL>` | 분석 & 저장 |
| `/list` | 메모 목록 |
| `/search <키워드>` | 검색 |
| `/delete <id>` | 삭제 |
| `/recommend` | 추천 (Claude 호출) |
| `/verbose on\|off` | 단계별 메시지 표시 |
| `/help` | 사용법 |

## 예시 Telegram 흐름

### 기본 모드 (URL 전송)
```
User: https://example.com/article

Bot: 📚 *저장 완료!*
     `AI 기술 동향 2026`

Bot: 🔍 *분석 완료!*
     📌 *AI 기술 동향 2026*
       • 2026년 주요 AI 트렌드 요약
       • 멀티모달 에이전트의 부상
       • 오픈소스 모델 경쟁 심화
     📂 카테고리: `기술`
     🏷 #AI #트렌드 #2026
```

### Verbose 모드
```
User: /verbose on
Bot: 🔧 Verbose 모드: `ON`

User: https://example.com/article

Bot: 🔧 *[🔍 Analyst]*
     ```json
     {"title":"AI 기술 동향 2026","bullets":[...],"category":"기술","tags":["AI"]}
     ```

Bot: 🔍 *분석 완료!*
     📌 *AI 기술 동향 2026*
     ...

Bot: 🔧 *[📚 Librarian]*
     ```json
     {"action":"saved","memo":{...}}
     ```

Bot: 📚 *저장 완료!*
     `AI 기술 동향 2026`
```
