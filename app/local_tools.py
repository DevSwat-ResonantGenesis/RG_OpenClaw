"""
OpenClaw Local Tool Executor
==============================

Executes tools LOCALLY on the user's machine.
Only results/steps are sent to the platform server.

Local tools:
  - web_search      → DuckDuckGo (no API key needed)
  - fetch_url       → httpx GET + HTML strip (local)
  - memory_write    → local SQLite + sync to platform
  - memory_read     → local SQLite first, fallback platform
  - execute_code    → local Python sandbox
  - deep_research   → web_search + fetch_url combo

Server-only tools (forwarded to platform):
  - google_calendar, google_drive, gmail_send, slack_send
  - image_generation, generate_image, generate_audio, generate_video
  - database_query, figma, browser_automation
  - Any tool not in the local set
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import traceback
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional
from pathlib import Path

import aiosqlite
import httpx

logger = logging.getLogger(__name__)

# ─── Local Memory DB ──────────────────────────────────────────────────

_DB_PATH: Optional[str] = None
_DB_INITIALIZED = False


async def _ensure_db(data_dir: str) -> str:
    """Initialize local SQLite memory database."""
    global _DB_PATH, _DB_INITIALIZED

    os.makedirs(data_dir, exist_ok=True)
    _DB_PATH = os.path.join(data_dir, "memory.db")

    if not _DB_INITIALIZED:
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    embedding_text TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    synced INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags)
            """)
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(id, content, tags, embedding_text)
            """)
            await db.commit()
        _DB_INITIALIZED = True
        logger.info(f"[LOCAL] Memory DB initialized at {_DB_PATH}")

    return _DB_PATH


# ─── HTML Stripping ──────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Strip HTML tags, scripts, styles — lightweight local version."""
    if len(html) > 500_000:
        html = html[:500_000]
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except ImportError:
        # Fallback: regex-based
        cleaned = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
        cleaned = unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned


# ─── Local Tool Implementations ──────────────────────────────────────

async def local_web_search(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Search the web using DuckDuckGo — runs entirely on user's machine."""
    query = tool_input.get("query") or tool_input.get("q") or tool_input.get("search_query", "")
    if not query:
        return {"error": "Missing 'query' parameter"}

    max_results = int(tool_input.get("max_results", 8))
    max_results = min(max_results, 20)

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        return {
            "query": query,
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                }
                for r in results
            ],
            "source": "local_duckduckgo",
        }
    except Exception as e:
        logger.warning(f"[LOCAL] web_search failed: {e}")
        return {"error": f"Local search failed: {e}", "fallback": True}


async def local_fetch_url(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a URL and extract text — runs entirely on user's machine."""
    url = tool_input.get("url", "")
    if not url:
        return {"error": "Missing 'url' parameter"}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; OpenClaw/1.0; +https://dev-swat.com)",
            "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.1",
        }
        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)

        if resp.status_code >= 400:
            return {"url": url, "status": resp.status_code, "error": f"HTTP {resp.status_code}"}

        content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        raw = resp.content or b""

        # Cap at 512KB
        if len(raw) > 512 * 1024:
            raw = raw[:512 * 1024]

        if content_type in ("text/html", "application/xhtml+xml"):
            text = _strip_html(raw.decode("utf-8", errors="ignore"))
        elif content_type.startswith("text/") or content_type in ("application/json", "application/xml"):
            text = raw.decode("utf-8", errors="ignore")
        else:
            return {"url": url, "status": resp.status_code, "content_type": content_type, "error": "Unsupported content type"}

        return {
            "url": url,
            "status": resp.status_code,
            "content_type": content_type,
            "text": text[:20000] if text else "",
            "source": "local",
        }
    except Exception as e:
        logger.warning(f"[LOCAL] fetch_url failed: {e}")
        return {"error": f"Local fetch failed: {e}", "fallback": True}


async def local_deep_research(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Deep research: search + fetch top results — runs locally."""
    query = tool_input.get("query") or tool_input.get("topic") or tool_input.get("subject", "")
    url = tool_input.get("url", "")

    results = {}

    if url:
        page_data = await local_fetch_url({"url": url})
        if page_data.get("fallback"):
            return page_data  # signal to use server
        results["page_content"] = page_data

    if query:
        search_data = await local_web_search({"query": query, "max_results": 5})
        if search_data.get("fallback"):
            return search_data  # signal to use server
        results["search_results"] = search_data
    elif not url:
        return {"error": "Provide 'query' or 'url'"}

    results["source"] = "local"
    return results


async def local_memory_write(tool_input: Dict[str, Any], data_dir: str, user_id: str = "") -> Dict[str, Any]:
    """Write memory to local SQLite DB on user's machine."""
    content = tool_input.get("content", "")
    if not content:
        return {"error": "Missing 'content' parameter"}

    tags = tool_input.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    metadata = tool_input.get("metadata", {})

    db_path = await _ensure_db(data_dir)
    mem_id = hashlib.sha256(f"{content[:200]}:{time.time()}".encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO memories (id, content, tags, metadata, embedding_text, created_at, updated_at, synced) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            (mem_id, content, json.dumps(tags), json.dumps(metadata), content[:500], now, now),
        )
        # Update FTS index
        await db.execute(
            "INSERT OR REPLACE INTO memories_fts (id, content, tags, embedding_text) VALUES (?, ?, ?, ?)",
            (mem_id, content, json.dumps(tags), content[:500]),
        )
        await db.commit()

    logger.info(f"[LOCAL] Memory written: {mem_id} ({len(content)} chars, tags={tags})")
    return {
        "success": True,
        "memory_id": mem_id,
        "stored_locally": True,
        "chars": len(content),
        "tags": tags,
        "source": "local_sqlite",
    }


async def local_memory_read(tool_input: Dict[str, Any], data_dir: str, user_id: str = "") -> Dict[str, Any]:
    """Read/search memory from local SQLite DB on user's machine."""
    query = tool_input.get("query", "")
    if not query:
        return {"error": "Missing 'query' parameter"}

    limit = min(int(tool_input.get("limit", 5)), 25)

    db_path = await _ensure_db(data_dir)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        # FTS search
        try:
            cursor = await db.execute(
                "SELECT m.id, m.content, m.tags, m.metadata, m.created_at FROM memories m JOIN memories_fts fts ON m.id = fts.id WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback: LIKE search
            cursor = await db.execute(
                "SELECT id, content, tags, metadata, created_at FROM memories WHERE content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (f"%{query}%", limit),
            )
            rows = await cursor.fetchall()

    memories = []
    for row in rows:
        memories.append({
            "id": row[0] if isinstance(row, tuple) else row["id"],
            "content": (row[1] if isinstance(row, tuple) else row["content"])[:2000],
            "tags": json.loads(row[2] if isinstance(row, tuple) else row["tags"]),
            "created_at": row[4] if isinstance(row, tuple) else row["created_at"],
        })

    return {
        "query": query,
        "memories": memories,
        "total": len(memories),
        "source": "local_sqlite",
    }


async def local_execute_code(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Python code locally on user's machine in a subprocess."""
    code = tool_input.get("code") or tool_input.get("python", "")
    if not code:
        return {"error": "Missing 'code' parameter"}

    # Run in subprocess with timeout for safety
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="ignore")[:5000],
            "stderr": stderr.decode("utf-8", errors="ignore")[:2000],
            "return_code": proc.returncode,
            "source": "local_python",
        }
    except asyncio.TimeoutError:
        return {"error": "Code execution timed out (30s)", "source": "local_python"}
    except Exception as e:
        return {"error": f"Local execution failed: {e}", "source": "local_python"}


# ─── Tool Registry ──────────────────────────────────────────────────

# Tools that run LOCALLY on user's machine
LOCAL_TOOLS = {
    "web_search": local_web_search,
    "fetch_url": local_fetch_url,
    "read_webpage": local_fetch_url,
    "scrape_page": local_fetch_url,
    "deep_research": local_deep_research,
    "execute_code": local_execute_code,
    "code_execution": local_execute_code,
}

# Tools that need local data_dir (memory)
LOCAL_MEMORY_TOOLS = {
    "memory_write": local_memory_write,
    "memory_read": local_memory_read,
}

# Tools that MUST go to server (need cloud APIs/credentials)
SERVER_ONLY_TOOLS = {
    "google_calendar", "google_drive", "gmail_send", "gmail_read",
    "slack_send", "slack_read",
    "image_generation", "generate_image", "generate_audio", "generate_video",
    "database_query", "figma", "browser_automation",
    "create_rabbit_post", "pdf_parse", "spreadsheet",
}


async def execute_tool_locally(
    tool_name: str,
    tool_input: Dict[str, Any],
    data_dir: str,
    user_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Try to execute a tool locally. Returns None if tool must go to server.
    Returns {"fallback": True, ...} if local execution failed and should retry on server.
    """
    # Memory tools need data_dir
    if tool_name in LOCAL_MEMORY_TOOLS:
        handler = LOCAL_MEMORY_TOOLS[tool_name]
        try:
            result = await handler(tool_input, data_dir=data_dir, user_id=user_id)
            if result.get("fallback"):
                return None  # signal server fallback
            return result
        except Exception as e:
            logger.warning(f"[LOCAL] {tool_name} failed locally: {e}")
            return None

    # Regular local tools
    if tool_name in LOCAL_TOOLS:
        handler = LOCAL_TOOLS[tool_name]
        try:
            result = await handler(tool_input)
            if result.get("fallback"):
                return None  # signal server fallback
            return result
        except Exception as e:
            logger.warning(f"[LOCAL] {tool_name} failed locally: {e}")
            return None

    # Not a local tool → must go to server
    return None
