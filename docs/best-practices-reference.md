# Implementation Best Practices Reference

> Working notes capturing the guidance pulled via Context7 research on November 23, 2025. Each subsection lists the most actionable rules, sample code, and a quick pointer back to the original source material.

## LangGraph v1.0 Alignment

- **Typed state contracts** – Define graph state as a `TypedDict` (or `pydantic.BaseModel`) and use annotations such as `Annotated[..., add_messages]` so LangGraph can merge partial updates correctly. Keep every mutation inside node functions so the runtime can diff inputs/outputs.

```python
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class ReviewState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    repo_url: str
```

- **Runtime injection** – Instantiate `langgraph.checkpoint.base.MemorySaver` or `PostgresSaver` outside the builder and pass it into `builder.add_edge(..., checkpoint=...)` or `builder.compile(checkpointer=...)` so every tool invocation is resumable.

```python
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(postgres_url)
workflow = builder.compile(checkpointer=checkpointer)
```

- **Declarative start/end nodes** – Always add `builder.set_entry_point()` and `builder.set_finish_point()` so the runtime can short-circuit when the finish condition is satisfied. This keeps state replay deterministic during time-travel debugging.

> Source: Context7 `/langchain-ai/langgraph` – "State & Configuration" and "Checkpointers" sections.

## LangChain Runtime & Observability

- **Runtime context** – Use `langchain_core.runnables.RunnableConfig` to propagate tracing metadata, and access it via `RunnableConfig.get("run_name")` inside agents when you need per-request logging.
- **Middleware hooks** – Register middleware with `langchain_core.runnables.RunnableLambda` or the new runtime `callback_manager` to intercept prompts/tool invocations (e.g., add guardrails, redact secrets, enforce budgets).
- **LangSmith tracing** – Wrap orchestration entry points with `@langsmith.traceable()` (or pass `LangSmithTracer` into `RunnableConfig`) to get step-level spans without editing every tool.

```python
from langchain_core.runnables import RunnableLambda
from langsmith import traceable

@traceable(name="repo-analysis-run")
def run_graph(config: RunnableConfig):
    enriched = config.copy(update={"metadata": {"tenant": "analysis"}})
    return graph.invoke(config=enriched)

policy_guard = RunnableLambda(lambda cfg, x: enforce_policies(cfg, x))
```

> Source: Context7 `/langchain-ai/langchain` – "Runtime", "Middleware", and "LangSmith Observability" guides.

## Persistence Stack

### SQLAlchemy (core + ORM)

- Prefer `async_sessionmaker` (2.0 style) to keep session lifecycle explicit; use `expire_on_commit=False` when the same objects feed downstream nodes.
- Create scoped sessions inside context managers so LangGraph nodes can `await` database work without leaking connections.

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(db_url, pool_size=10, max_overflow=5)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def fetch_repo(repo_id: str):
    async with SessionLocal() as session:
        return await session.get(Repository, repo_id)
```

### psycopg2

- Use `psycopg2.pool.SimpleConnectionPool` for scripts and `ThreadedConnectionPool` for concurrency; always `putconn` in `finally` blocks.
- Disable implicit autocommit; instead call `conn.autocommit = False` and commit explicitly so retries can roll back cleanly.

```python
from psycopg2.pool import ThreadedConnectionPool
pool = ThreadedConnectionPool(1, 10, dsn=postgres_url)

conn = pool.getconn()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        conn.commit()
finally:
    pool.putconn(conn)
```

### Alembic

- Keep `env.py` focused on config + target metadata; import metadata from `src.storage.models` to ensure autogenerate sees it.
- Use `context.configure(compare_type=True, render_as_batch=True)` to catch column type drift and to support SQLite-based tests.
- Gate large migrations with branch labels so parallel work streams remain mergeable.

```python
from alembic import context
from src.storage.base import Base

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
```

> Sources: Context7 `/sqlalchemy/sqlalchemy`, `/psycopg/psycopg2`, `/sqlalchemy/alembic` – async sessions, pooling, and migration env recipes.

## Supporting Libraries

### requests

- Set per-request or tuple `(connect_timeout, read_timeout)` values.
- Mount `HTTPAdapter` with `Retry` to centralize idempotent retries.
- Disable `Session.trust_env` when you do not want netrc/proxy leakage.
- Pin TLS trust by setting `Session.verify` or client certificates once on the session.

```python
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

session = Session()
session.trust_env = False
session.verify = "C:/certs/bitwarden-ca.pem"
retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[502, 503, 504], allowed_methods={"GET","POST"})
session.mount("https://", HTTPAdapter(max_retries=retries))
response = session.get(target_url, timeout=(3.05, 15))
```

> Source: Context7 `/psf/requests` – advanced user guide & cookbook.

### PyYAML

- Always use `safe_load` / `safe_load_all` for untrusted input; `load` requires an explicit loader.
- Leverage `CLoader` / `CSafeLoader` when LibYAML is installed for speed.
- Prefer `safe_dump` (or `safe_dump_all`) with `sort_keys=False` to preserve human-friendly ordering.

```python
import yaml

with open("config.yaml", "r", encoding="utf-8") as fh:
    cfg = yaml.safe_load(fh)

yaml.safe_dump(cfg, open("out.yaml", "w", encoding="utf-8"), sort_keys=False)
```

> Source: Context7 `/yaml/pyyaml` – README and load() deprecation notice.

### tenacity

- Combine `stop_after_attempt`, `wait_fixed`/exponential waits, and result/exception filters for deterministic retries.
- Pass `reraise=True` so the last exception surfaces when retries exhaust.
- Use `before_log` to make each retry observable.

```python
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_log

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=8),
    retry=retry_if_exception_type(TransientError),
    before=before_log(logger, logging.INFO),
    reraise=True,
)
async def fetch_with_retry(client, payload):
    return await client.send(payload)
```

> Source: Context7 `/jd/tenacity` – README & docs.

### radon

- Automate `radon cc` and `radon mi` in CI; filter with `--min B --max F` to surface only risky blocks.
- Use API helpers (`cc_visit`, `ComplexityVisitor`) to enforce per-module budgets.

```powershell
radon cc src --min C --max F --average
radon mi src --fail 70
```

> Source: Context7 `/rubik/radon` – CLI & API docs.

### packaging specs (dependency metadata)

- Express compatible releases with `~=` and combine with exclusion clauses to avoid known-bad builds.
- Attach environment markers for platform or interpreter-specific deps.
- Use extras to keep optional integrations isolated.

```text
requests[security]>=2.31.0; python_version >= "3.9"
psycopg[binary]==3.2.* ; sys_platform == "win32"
tomli>=1.1.0 ; python_version < "3.11"
```

> Source: Context7 `/pypa/packaging.python.org` – dependency & version specifier specs.

### tomli / tomllib

- Read TOML files in binary mode for spec-compliant decoding.
- Provide a shim that imports stdlib `tomllib` on 3.11+ and falls back to `tomli` elsewhere.
- Capture invalid config early by trapping `TOMLDecodeError`.

```python
import sys
if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on <3.11
    import tomli as tomllib

with open("settings.toml", "rb") as fh:
    settings = tomllib.load(fh)
```

> Source: Context7 `/hukkin/tomli` – README & tomllib notes.

---
**Next steps**: wire the above into contributor docs (for expectations) and automation (radon gates, retry helpers, SQLAlchemy session factory). Let me know if you want follow-up PR checklists or code templates.
