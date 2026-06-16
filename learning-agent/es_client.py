"""Round 1: ES direct access — fetch all chunks for a file by fileMd5."""
from elasticsearch import Elasticsearch
import config


def get_es_client() -> Elasticsearch:
    return Elasticsearch(
        f"{config.ES_SCHEME}://{config.ES_HOST}:{config.ES_PORT}",
        basic_auth=(config.ES_USERNAME, config.ES_PASSWORD),
    )


def fetch_all_chunks(file_md5: str, max_chunks: int = 100) -> list[dict]:
    """Return all chunks for a file, sorted by chunkId (preserves reading order)."""
    es = get_es_client()
    result = es.search(index=config.ES_INDEX, body={
        "query": {"term": {"fileMd5": file_md5}},
        "size": max_chunks,
        "sort": [{"chunkId": "asc"}],
    })
    hits = result["hits"]["hits"]
    return [{"chunkId": h["_source"]["chunkId"],
             "pageNumber": h["_source"].get("pageNumber"),
             "textContent": h["_source"]["textContent"]}
            for h in hits]
