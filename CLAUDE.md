# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LetsLearn is a Duolingo-style AI learning agent built on top of a production RAG infrastructure. Users upload textbook PDFs (pre-split by chapter), and the system generates interactive quiz cards with AI explanations and multiple-choice questions, tracks learning progress, and remembers mistakes across sessions via MySQL-backed long-term memory.

**Tech Stack**: Spring Boot (Java 17) + Vue 3 (TypeScript) + Python FastAPI + LangGraph + MySQL + Elasticsearch + Kafka + Redis + MinIO.

## Quick Start

```bash
# Start all services
cd docs && docker compose up -d

# Backend
mvn spring-boot:run

# Python Agent (quiz generation)
cd learning-agent && source venv/bin/activate && uvicorn main:app --port 8000

# Frontend
cd frontend && pnpm install && pnpm dev
```

Frontend dev server: `http://localhost:9527`. Backend API: `http://localhost:8081`. Python Agent: `http://localhost:8000`.

## LetsLearn: AI Learning Agent

### Architecture

```
User uploads chapter PDF
  → Kafka async pipeline (parse → chunk → embed → ES index)
  → User clicks "开始学习"
  → Frontend → Python Agent :8000 (LangGraph)
     → Round 1: ES direct query (fileMd5 term filter) → all chunks
     → Round 2: LLM summarize → N knowledge points
     → Round 3: Send fan-out (N parallel) → each: ES search + LLM generate 1 card
     → SSE streaming progress → frontend renders quiz cards
  → User answers → static evaluation (pre-generated isCorrect + feedback)
  → Save to MySQL (quiz_sessions + quiz_mistakes)
```

### learning-agent/ (Python FastAPI + LangGraph)

```
learning-agent/
├── main.py              # FastAPI: quiz generation (POST + SSE stream), quiz persistence proxy
├── graph_learning.py    # LangGraph StateGraph: summarize → Send fan-out → generate
├── state.py             # TypedDict state with Annotated reducers
├── es_client.py         # ES direct query (Round 1: term filter fileMd5)
├── search.py            # Java /api/v1/search/hybrid wrapper (Round 2: hybrid search)
├── prompts.py           # SUMMARIZE_PROMPT, MISTAKE_SUMMARIZE_PROMPT, SINGLE_CARD_PROMPT
└── config.py            # Reads .env for ES/LLM/Java credentials
```

**Key endpoints**:
- `POST /api/quiz/generate` — one-shot quiz generation
- `GET /api/quiz/generate/stream?fileMd5=X` — SSE streaming with real-time progress
- `POST /api/quiz/complete` — save quiz results + mistakes to MySQL (proxies to Java)
- `GET /api/quiz/history?fileMd5=X` — all quiz records for a file
- `GET /api/quiz/mistakes?fileMd5=X` — mistake cards for review generation

**LangGraph Send fan-out**: The summarize node identifies N knowledge points. A conditional edge spawns N parallel `generate_one_card` tasks via `Send()`. Each task independently searches ES + calls LLM. Results accumulate via `operator.add` reducer. Total time ~14s for 15 cards (parallel threads).

**Mistake review (Phase 3.5)**: Before summarize, reads `quiz_mistakes` table. If mistakes exist, uses `MISTAKE_SUMMARIZE_PROMPT` to inject mistake titles into the knowledge point list. During card generation, title-matched mistakes skip LLM and return pre-existing cards with `isMistake: true`.

**Multi-tenant (Phase 4.0)**: Frontend sends `X-User-Id` header (extracted from JWT). Python Agent forwards as `?userId=X` query param to Java. Java QuizController uses `resolveUserId(paramUserId, jwtUserId)` for data isolation. Admin JWT provides authentication; userId provides data scoping.

### Java Backend: Quiz Persistence

**New entities** (under `com.letslearnco.letslearn`):
- `QuizSession.java` — `quiz_sessions` table: user_id, file_md5, cards_json, user_answers_json, correct_count, accuracy
- `QuizMistake.java` — `quiz_mistakes` table: user_id, file_md5, card_title, question, options_json, correct_label
- `QuizController.java` — REST API: save, latest, check, history, detail, save-mistakes, get-mistakes

**Security**: `/api/v1/quiz/**` is permitted in SecurityConfig + OrgTagAuthorizationFilter.

### Frontend: Learning UI

**Key pages**:
- `/knowledge-base` — file list + "开始学习" / "Quiz历史" buttons
- `/learning?fileMd5=X` — split-screen: quiz cards (left) + chat sidebar (right)
- `/quiz-center` — Phase 3 dual-list history browser (files | quiz records | preview panel)
- `/quiz-history?fileMd5=X` — Phase 2.5 read-only quiz replay (long scroll)

**Chat sidebar (Phase 2.3A)**: Reuses Java's existing chat store (`useChatStore`) and `ChatMessage` component. New session per file. Select-to-search: mouseup → floating "问问Agent" button → pre-fills sidebar input with card title + selected text.

**SSE progress bar (Phase 2.4)**: `fetchGenerateQuizStream` reads SSE via ReadableStream reader. Real-time progress: "已生成 5/15 张卡片...". Naive UI `<NProgress>` with percentage.

**Quiz card interaction**: Duolingo-style — user selects option → clicks "提交" → result panel slides up with ✅/❌ + feedback → "下一题". All evaluation is client-side (pre-generated `isCorrect` + `feedback` per option).

## Local Runtime Rules

### Backend

- Prefer compiling to trigger hot reload: `mvn -q -DskipTests compile`
- Only restart if explicitly asked or hot reload isn't active
- Backend runs on `localhost:8081`

### Frontend

- Usually already running in dev mode on `localhost:9527`
- Vite proxies `/proxy-default/*` → Java `http://localhost:8081`

### Browser Verification

Common pages:
- `http://localhost:9527/#/chat` — RAG chat assistant
- `http://localhost:9527/#/knowledge-base` — file management + learning entry
- `http://localhost:9527/#/quiz-center` — quiz history browser

When debugging, always check: network requests, console output, backend logs, and DB state.

## Configuration Sources

- Backend: repo root `.env` → `application.yml` → `application-dev.yml`
- Frontend: `frontend/.env` → Vite proxy config
- Python Agent: reads repo root `.env` via `config.py` → `DotenvEnvironmentPostProcessor`

## Repo-Specific Notes

- **Chat history**: Redis for short-lived context (20 messages, 7d TTL). MySQL for persistent storage.
- **Multi-tenant**: Quiz data is user-scoped via `X-User-Id` header. RAG search is admin-scoped (existing infrastructure).
- **Quiz data flow**: Frontend → Python Agent (port 8000) → Java (port 8081) → MySQL. Python Agent uses admin JWT for auth + explicit userId for data scoping.
- **ES queries**: Round 1 (fetch_all_chunks) uses direct ES query with fileMd5 term filter + userId/isPublic permission filter. Round 2 uses Java's built-in hybrid search API.

## Preferred Commands

```bash
# Backend compile only
mvn -q -DskipTests compile

# Backend tests
mvn test

# Frontend lint
cd frontend && pnpm exec eslint <file>

# Frontend type check
cd frontend && pnpm typecheck

# Python Agent restart
cd learning-agent && source venv/bin/activate && uvicorn main:app --port 8000
```

## What To Avoid

- Don't restart backend unnecessarily (use hot reload)
- Don't assume Redis means durable persistence (it's cache with TTL)
- Don't claim a UI fix is done without checking the live page
- Don't change shell startup files or global environment for temporary tests
- Don't rely only on source inspection when runtime evidence is cheap to collect

## Done Criteria

A task is complete when:
1. Code changed
2. Backend compiled (or Python syntax verified)
3. Browser re-tested
4. Network response confirmed
5. Any relevant DB/Redis state checked when data-related
