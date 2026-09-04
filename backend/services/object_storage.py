"""
Emergent Object Storage helper.

Replaces pod-local file writes so uploads survive redeploys.
- put_uploaded_file(category, filename, data, content_type)
    - Uploads bytes to Emergent object storage.
    - Records mapping {category, filename, storage_path, content_type} in db.storage_files.
- serve_uploaded_file(category, filename)
    - Looks up mapping in db.storage_files and returns a FastAPI Response.
- fetch_bytes(storage_path)
    - Low-level download (used when we already have the storage_path).

All uploaded categories the app previously wrote under `static/` or `uploads/`
are routed through this module so we no longer touch the pod filesystem.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import requests
from fastapi import HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

APP_NAME = "mddrc-training"

STORAGE_BASE = (
    (os.environ.get("INTEGRATION_PROXY_URL") or "").strip()
    or "https://integrations.emergentagent.com"
)
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

_storage_key: Optional[str] = None


def _init_storage(force: bool = False) -> str:
    """Mint or reuse a session-scoped storage key."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY missing from backend env")
    resp = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": EMERGENT_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _put(path: str, data: bytes, content_type: str) -> dict:
    key = _init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    if resp.status_code == 404:
        # Cached key went dead — force re-init once.
        key = _init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def fetch_bytes(storage_path: str) -> tuple[bytes, str]:
    """Download an object by storage path. Returns (content_bytes, content_type)."""
    key = _init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{storage_path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    if resp.status_code == 404:
        key = _init_storage(force=True)
        resp = requests.get(
            f"{STORAGE_URL}/objects/{storage_path}",
            headers={"X-Storage-Key": key},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def put_uploaded_file(
    db,
    category: str,
    filename: str,
    data: bytes,
    content_type: str,
) -> dict:
    """
    Upload bytes to object storage under `{APP_NAME}/uploads/{category}/{filename}`
    and record the mapping in db.storage_files so serve_uploaded_file() can find it.
    """
    storage_path = f"{APP_NAME}/uploads/{category}/{filename}"
    result = _put(storage_path, data, content_type)

    doc = {
        "category": category,
        "filename": filename,
        "storage_path": result.get("path", storage_path),
        "content_type": content_type,
        "size": result.get("size"),
    }
    await db.storage_files.update_one(
        {"category": category, "filename": filename},
        {"$set": doc},
        upsert=True,
    )
    return doc


async def serve_uploaded_file(db, category: str, filename: str) -> Response:
    """Return a FastAPI Response with the file bytes from object storage."""
    record = await db.storage_files.find_one(
        {"category": category, "filename": filename}, {"_id": 0}
    )
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content, ctype = fetch_bytes(record["storage_path"])
    except requests.HTTPError as e:
        logger.error(f"Object storage fetch failed: {e}")
        raise HTTPException(status_code=404, detail="File not found in storage")

    return Response(
        content=content,
        media_type=record.get("content_type") or ctype,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


async def load_bytes(db, category: str, filename: str) -> Optional[bytes]:
    """Convenience helper for server-side code that needs the raw bytes."""
    record = await db.storage_files.find_one(
        {"category": category, "filename": filename}, {"_id": 0}
    )
    if not record:
        return None
    content, _ = fetch_bytes(record["storage_path"])
    return content
