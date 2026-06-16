"""LetsLearn — Phase 1 MVP: Learning quiz generation endpoint."""
import json
import uuid
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph_learning import build_learning_graph

app = FastAPI(title="LetsLearn Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

learning_graph = build_learning_graph()


class QuizGenerateRequest(BaseModel):
    fileMd5: str


@app.get("/api/quiz/generate/stream")
async def generate_quiz_stream(fileMd5: str = Query(...), request: Request = None):
    """SSE streaming: real-time progress as each card is generated."""
    import uuid
    uid = _get_x_user_id(request) if request else ""
    async def event_stream():
        initial_state = {
            "file_md5": fileMd5,
            "user_id": uid,
            "all_chunks": [],
            "all_chunks_text": "",
            "key_points": [],
            "key_point": "",
            "cards": [],
            "error": "",
        }
        thread_id = f"quiz-{fileMd5}-{uuid.uuid4().hex[:8]}"

        total = None
        cards_done = 0
        try:
            async for chunk in learning_graph.astream(
                initial_state,
                {"configurable": {"thread_id": thread_id}},
                stream_mode="updates",
            ):
                # stream_mode="updates" yields {node_name: node_return} dicts
                for node_name, node_output in chunk.items():
                    if node_name == "summarize" and total is None:
                        total = len(node_output.get("key_points", []))
                        print(f"[SSE] start total={total}")
                        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

                    if node_name == "generate_one_card":
                        new_cards = node_output.get("cards", [])
                        cards_done += len(new_cards)
                        if total:
                            print(f"[SSE] progress {cards_done}/{total}")
                            yield f"data: {json.dumps({'type': 'progress', 'done': cards_done, 'total': total})}\n\n"

            # Collect final result
            final = await learning_graph.aget_state({"configurable": {"thread_id": thread_id}})
            cards = final.values.get("cards", []) if final.values else []
            yield f"data: {json.dumps({'type': 'complete', 'cards': cards})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/quiz/generate")
async def generate_quiz(req: QuizGenerateRequest, request: Request = None):
    """Generate learning quiz cards for a given file.

    Flow:
      1. ES term query -> all chunks for the file
      2. LLM summarize -> identify N key knowledge points
      3. Send fan-out -> parallel hybrid search for each key point
      4. LLM generate -> quiz cards with AI explanation + 4-option MC
    """
    initial_state = {
        "file_md5": req.fileMd5,
        "user_id": _get_x_user_id(request) if request else "",
        "all_chunks": [],
        "all_chunks_text": "",
        "key_points": [],
        "key_point": "",
        "detailed_searches": [],
        "cards": [],
        "error": "",
    }

    thread_id = f"quiz-{req.fileMd5}-{uuid.uuid4().hex[:8]}"
    result = await learning_graph.ainvoke(initial_state, {"configurable": {"thread_id": thread_id}})

    if result.get("error"):
        return {"error": result["error"], "cards": []}

    return {
        "fileMd5": req.fileMd5,
        "key_points": result["key_points"],
        "cards": result["cards"],
    }


class QuizCompleteRequest(BaseModel):
    fileMd5: str
    fileName: str
    cards: list
    userAnswers: list  # [{cardIndex, selectedLabel, isCorrect}]


@app.post("/api/quiz/complete")
async def complete_quiz(req: QuizCompleteRequest, request: Request = None):
    """Proxy to Java: save quiz results (pure DB write, no LLM)."""
    import httpx
    token = _get_agent_token()
    uid = _get_x_user_id(request) if request else ""
    save_url = f"{JAVA_BASE}/api/v1/quiz/save"
    if uid: save_url += f"?userId={uid}"
    resp = httpx.post(
        save_url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "fileMd5": req.fileMd5,
            "fileName": req.fileName,
            "cards": req.cards,
            "userAnswers": req.userAnswers,
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    # Save mistake cards to quiz_mistakes table
    mistakes = [a for a in req.userAnswers if not a.get("isCorrect")]
    if mistakes:
        mistake_cards = []
        for m in mistakes:
            card = req.cards[m["cardIndex"]] if m["cardIndex"] < len(req.cards) else None
            if card:
                correct_label = next((o["label"] for o in card.get("options", []) if o.get("isCorrect")), "")
                mistake_cards.append({
                    "title": card.get("title", ""),
                    "aiExplanation": card.get("aiExplanation", ""),
                    "question": card.get("question", ""),
                    "options": card.get("options", []),
                    "correctLabel": correct_label,
                })
        if mistake_cards:
            quiz_id = result.get("quizId")
            ms_url = f"{JAVA_BASE}/api/v1/quiz/save-mistakes"
            if uid: ms_url += f"?userId={uid}"
            ms_resp = httpx.post(
                ms_url,
                headers={"Authorization": f"Bearer {token}"},
                json={"fileMd5": req.fileMd5, "quizId": quiz_id, "mistakes": mistake_cards},
                timeout=30,
            )
            ms_resp.raise_for_status()

    return result


_agent_token_cache = None
JAVA_BASE = "http://localhost:8081"


def _get_x_user_id(request) -> str:
    """Extract X-User-Id from incoming request."""
    if request:
        uid = request.headers.get("X-User-Id", "")
        if uid and uid.isdigit(): return uid
    return ""

def _get_agent_token() -> str:
    import httpx as _httpx
    global _agent_token_cache
    if _agent_token_cache:
        return _agent_token_cache
    from config import AGENT_USER, AGENT_PASS
    r = _httpx.post(f"{JAVA_BASE}/api/v1/users/login", json={
        "username": AGENT_USER, "password": AGENT_PASS
    })
    r.raise_for_status()
    _agent_token_cache = r.json()["data"]["token"]
    return _agent_token_cache


@app.get("/api/quiz/check")
async def check_quiz(fileMd5: str = Query(...), request: Request = None):
    import httpx
    token = _get_agent_token()
    params = {"fileMd5": fileMd5}
    uid = _get_x_user_id(request)
    if uid: params["userId"] = uid
    resp = httpx.get(f"{JAVA_BASE}/api/v1/quiz/check", params=params,
                     headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


@app.get("/api/quiz/latest")
async def latest_quiz(fileMd5: str = Query(...), request: Request = None):
    import httpx
    token = _get_agent_token()
    params = {"fileMd5": fileMd5}
    uid = _get_x_user_id(request)
    if uid: params["userId"] = uid
    resp = httpx.get(f"{JAVA_BASE}/api/v1/quiz/latest", params=params,
                     headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


@app.get("/api/quiz/history")
async def get_quiz_history(fileMd5: str = Query(...), request: Request = None):
    import httpx
    token = _get_agent_token()
    params = {"fileMd5": fileMd5}
    uid = _get_x_user_id(request)
    if uid: params["userId"] = uid
    resp = httpx.get(f"{JAVA_BASE}/api/v1/quiz/history", params=params,
                     headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


@app.get("/api/quiz/detail")
async def get_quiz_detail(quizId: int = Query(...), request: Request = None):
    import httpx
    token = _get_agent_token()
    params = {"quizId": quizId}
    uid = _get_x_user_id(request)
    if uid: params["userId"] = uid
    resp = httpx.get(f"{JAVA_BASE}/api/v1/quiz/detail", params=params,
                     headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


@app.get("/api/quiz/mistakes")
async def get_mistakes(fileMd5: str = Query(...), request: Request = None):
    import httpx
    token = _get_agent_token()
    params = {"fileMd5": fileMd5}
    uid = _get_x_user_id(request)
    if uid: params["userId"] = uid
    resp = httpx.get(f"{JAVA_BASE}/api/v1/quiz/mistakes", params=params,
                     headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


@app.get("/api/quiz/health")
async def health():
    return {"status": "ok"}
