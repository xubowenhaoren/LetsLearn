"""Read configuration from Java .env file."""
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

def _parse_dotenv(path: Path) -> dict[str, str]:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env

_env = _parse_dotenv(ENV_FILE)

# Elasticsearch
ES_HOST = _env.get("ELASTICSEARCH_HOST", "localhost")
ES_PORT = int(_env.get("ELASTICSEARCH_PORT", "9200"))
ES_SCHEME = _env.get("ELASTICSEARCH_SCHEME", "http")
ES_USERNAME = _env.get("ELASTICSEARCH_USERNAME", "elastic")
ES_PASSWORD = _env.get("ELASTICSEARCH_PASSWORD", "")
ES_INDEX = "knowledge_base"

# Java backend
JAVA_BASE = "http://localhost:8081"
AGENT_USER = _env.get("ADMIN_BOOTSTRAP_USERNAME", "admin")
AGENT_PASS = _env.get("ADMIN_BOOTSTRAP_PASSWORD", "")

# DeepSeek LLM
LLM_BASE_URL = _env.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
LLM_MODEL = _env.get("DEEPSEEK_API_MODEL", "deepseek-chat")
LLM_API_KEY = _env.get("DEEPSEEK_API_KEY", "")

# Quiz generation
MAX_CARDS = 15
CHUNKS_PER_SEARCH = 5
