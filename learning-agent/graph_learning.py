"""LangGraph: Learning quiz generation with per-card Send fan-out."""
import json
import httpx
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from langgraph.checkpoint.memory import InMemorySaver

import config
import prompts
from es_client import fetch_all_chunks
from search import hybrid_search
from state import LearningQuizState


# ── Node: fetch_chunks ──────────────────────────────────────────────
def fetch_chunks_node(state: LearningQuizState) -> dict:
    """Round 1: Get ALL chunks for the file from ES."""
    file_md5 = state["file_md5"]
    chunks = fetch_all_chunks(file_md5)

    if not chunks:
        return {"error": f"No chunks found for fileMd5={file_md5}"}

    chunk_texts = [f"[Chunk {c['chunkId']} / Page {c.get('pageNumber', '?')}]\n{c['textContent']}"
                   for c in chunks]
    all_text = "\n\n---\n\n".join(chunk_texts)
    return {"all_chunks": chunks, "all_chunks_text": all_text}


# ── Node: summarize ─────────────────────────────────────────────────
def summarize_node(state: LearningQuizState) -> dict:
    """LLM reads all chunks, identifies N key knowledge points."""
    if state.get("error"):
        return {}

    # Dynamic N based on file size
    n_chunks = len(state["all_chunks"])
    if n_chunks < 8:
        N = min(3, n_chunks)
    elif n_chunks <= 20:
        N = max(5, n_chunks // 3)
    else:
        N = max(8, min(15, n_chunks // 2))

    # Check for mistake history
    mistake_titles = _fetch_mistake_titles(state["file_md5"], state.get("user_id", ""))
    if mistake_titles:
        prompt = prompts.MISTAKE_SUMMARIZE_PROMPT.format(
            N=N,
            mistake_titles=", ".join(mistake_titles),
            chunks_text=state["all_chunks_text"][:12000],
        )
    else:
        prompt = prompts.SUMMARIZE_PROMPT.format(
            N=N,
            chunks_text=state["all_chunks_text"][:12000],
        )

    key_points = None
    for attempt in range(3):
        resp = httpx.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json={
                "model": config.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000,
            },
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"]
        finish_reason = body["choices"][0].get("finish_reason", "unknown")
        print(f"[summarize] finish={finish_reason}, len={len(content)}, N={N}")
        try:
            key_points = _parse_json_array(content)
            break
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            print(f"[summarize] JSON retry {attempt+1}/2")
    return {"key_points": key_points}


# ── Conditional edge: fan-out to generate_one_card ──────────────────
def continue_to_generate(state: LearningQuizState):
    """Spawn one parallel task per key_point: search + generate 1 card."""
    if state.get("error"):
        return []
    return [Send("generate_one_card", {"key_point": kp, "file_md5": state["file_md5"], "user_id": state.get("user_id", "")}) for kp in state["key_points"]]


# ── Node: generate_one_card (runs N times in parallel) ─────────────
def generate_one_card_node(state: LearningQuizState) -> dict:
    """Search ES + LLM generate ONE card for a specific key_point."""
    kp = state.get("key_point", "")
    if not kp:
        return {"cards": []}

    # Check if this key_point matches a previous mistake → reuse directly
    mistake_card = _find_mistake_card(kp)
    if mistake_card:
        mistake_card["isMistake"] = True
        # Ensure options have correct structure
        for o in mistake_card.get("options", []):
            o["isCorrect"] = (o.get("label") == mistake_card.get("correctLabel", ""))
        return {"cards": [mistake_card]}

    try:
        # 1. Search ES for this knowledge point
        results = hybrid_search(kp, top_k=config.CHUNKS_PER_SEARCH)
        snippets = []
        for r in results:
            text = r.get("textContent", "")[:800]
            if text:
                snippets.append(text)
        detailed_content = "\n\n---\n\n".join(snippets)

        # 2. Generate one card via LLM (retry on JSON parse errors)
        prompt = prompts.SINGLE_CARD_PROMPT.format(
            key_point=kp,
            detailed_content=detailed_content[:5000],
        )

        card = None
        for attempt in range(3):
            resp = httpx.post(
                f"{config.LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
                json={
                    "model": config.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 4096,
                },
                timeout=300,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                card = _parse_single_json(content)
                break
            except json.JSONDecodeError:
                if attempt == 2:
                    print(f"[generate_one_card] Giving up on '{kp}' after 3 JSON failures")
                    return {"cards": []}
                print(f"[generate_one_card] JSON retry {attempt+1}/2 for '{kp}'")
        card = _shuffle_single_card(card)
        return {"cards": [card]}

    except Exception as e:
        print(f"[generate_one_card] FAILED for '{kp}': {e}")
        # Return a placeholder so other cards are not lost
        return {"cards": [{
            "title": kp,
            "aiExplanation": f"(生成失败: {e})",
            "question": "生成失败",
            "options": [
                {"label": "A", "text": "—", "isCorrect": True, "feedback": ""}
            ]
        }]}


# ── Build graph ─────────────────────────────────────────────────────
def build_learning_graph() -> StateGraph:
    """Construct the learning quiz LangGraph with per-card Send fan-out."""
    graph = StateGraph(LearningQuizState)

    graph.add_node("fetch_chunks", fetch_chunks_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("generate_one_card", generate_one_card_node)

    graph.set_entry_point("fetch_chunks")
    graph.add_edge("fetch_chunks", "summarize")
    graph.add_conditional_edges("summarize", continue_to_generate, ["generate_one_card"])
    graph.add_edge("generate_one_card", END)

    return graph.compile(checkpointer=InMemorySaver())


# ── Helpers ─────────────────────────────────────────────────────────
# ── Mistake helpers ─────────────────────────────────────────────────
_mistake_cache: dict = {}  # (user_id, file_md5) -> list of mistake card dicts


def _fetch_mistake_titles(file_md5: str, user_id: str = "") -> list[str]:
    """Return mistake card titles for a (user, file), or empty list."""
    global _mistake_cache
    cache_key = (user_id, file_md5)
    if cache_key in _mistake_cache:
        return [m["title"] for m in _mistake_cache[cache_key]]

    try:
        import httpx as _httpx
        from main import _get_agent_token, JAVA_BASE
        token = _get_agent_token()
        params = {"fileMd5": file_md5}
        if user_id:
            params["userId"] = user_id
        resp = _httpx.get(f"{JAVA_BASE}/api/v1/quiz/mistakes",
                          params=params,
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("hasMistakes") and data.get("mistakes"):
            cards = data["mistakes"]
            _mistake_cache[cache_key] = cards
            return [c["title"] for c in cards]
    except Exception as e:
        print(f"[_fetch_mistake_titles] Failed: {e}")
    return []


def _find_mistake_card(key_point: str) -> dict | None:
    """Return a matching mistake card for the given key_point, or None."""
    for cache_key, cards in _mistake_cache.items():
        for card in cards:
            # Fuzzy match: title contains key_point or vice versa
            if key_point in card.get("title", "") or card.get("title", "") in key_point:
                return dict(card)  # copy
    return None


def _shuffle_single_card(card: dict) -> dict:
    """Shuffle options so correct answer is randomly positioned in one card."""
    import random as _random
    options = card.get("options", [])
    if not options:
        return card
    correct_idx = next((i for i, o in enumerate(options) if o.get("isCorrect")), 0)
    target_idx = _random.randint(0, len(options) - 1)
    if target_idx != correct_idx:
        options[correct_idx], options[target_idx] = options[target_idx], options[correct_idx]
    for i, o in enumerate(options):
        o["label"] = chr(ord("A") + i)
    return card


def _shuffle_correct_answer(cards: list) -> list:
    """Post-process: ensure correct answer is randomly positioned per card."""
    import random as _random
    for card in cards:
        options = card.get("options", [])
        if not options:
            continue
        correct_idx = next((i for i, o in enumerate(options) if o.get("isCorrect")), 0)
        target_idx = _random.randint(0, len(options) - 1)
        if target_idx != correct_idx:
            options[correct_idx], options[target_idx] = options[target_idx], options[correct_idx]
        for i, o in enumerate(options):
            o["label"] = chr(ord("A") + i)
    return cards


def _parse_single_json(raw: str) -> dict:
    """Parse a single JSON object from LLM output (not array)."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines)
    # Try direct parse first, then find {...}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
        raise


def _parse_json_array(raw: str) -> list:
    """Extract a JSON array from LLM output."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        print(f"[_parse_json_array] Failed at char {e.pos}: {raw[max(0,e.pos-80):e.pos+80]}")
        raise
