"""Round 2: Call Java /api/v1/search/hybrid with JWT auth."""
import httpx
import config


def _get_token() -> str:
    """Login as admin and return JWT token."""
    resp = httpx.post(
        f"{config.JAVA_BASE}/api/v1/users/login",
        json={"username": config.AGENT_USER, "password": config.AGENT_PASS},
    )
    resp.raise_for_status()
    body = resp.json()
    # token is nested in data.token
    token = body.get("data", {}).get("token") or body.get("token")
    if not token:
        raise RuntimeError(f"Login failed: {body}")
    return token


_token_cache: str | None = None


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Search Java knowledge base using hybrid (KNN + BM25) search."""
    global _token_cache
    if _token_cache is None:
        _token_cache = _get_token()

    resp = httpx.get(
        f"{config.JAVA_BASE}/api/v1/search/hybrid",
        params={"query": query, "topK": top_k},
        headers={"Authorization": f"Bearer {_token_cache}"},
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", [])
