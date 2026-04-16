#!/usr/bin/env python3
"""
Three-layer context caching for novel-writing pipeline.

L1 (Session Cache): In-memory dict, cleared after chapter completes.
L2 (Context Reuse): SHA-256 hash of intent + truth files vs context-meta.json.
L3 (Lazy Load): Genre profile / style guide loaded on first access, cached for session.

Invalidation: on_truth_file_update() clears L1 + deletes context-meta.json.
Cache miss falls through to normal file read silently.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _log(layer: str, event: str, detail: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[Cache {layer}] [{event}] {detail} ({ts})")


# --- Layer 1: Session Cache (in-memory, per-chapter) ---

class SessionCache:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}  # filePath -> {content, timestamp}

    def read(self, file_path: str) -> str:
        entry = self._store.get(file_path)
        if entry is not None:
            _log("L1:Session", "HIT", file_path)
            return entry["content"]
        _log("L1:Session", "MISS", file_path)
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            self._store[file_path] = {
                "content": content,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            return content
        except OSError:
            return ""

    def invalidate(self, file_path: str) -> None:
        self._store.pop(file_path, None)
        _log("L1:Session", "CLEAR", file_path)

    def clear(self) -> None:
        size = len(self._store)
        self._store.clear()
        _log("L1:Session", "CLEAR", f"all {size} entries")

    @property
    def size(self) -> int:
        return len(self._store)


# --- Layer 2: Context Reuse (file-based, cross-chapter) ---

class ContextReuse:
    def _hash_file(self, file_path: str) -> str:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            return hashlib.sha256(content.encode()).hexdigest()
        except OSError:
            return ""

    def _hash_files(self, file_paths: list[str]) -> str:
        h = hashlib.sha256()
        for fp in file_paths:
            try:
                content = Path(fp).read_text(encoding="utf-8")
                h.update(f"<<{fp}>>{content}".encode())
            except OSError:
                h.update(f"<<{fp}>>__MISSING__".encode())
        return h.hexdigest()

    def check(self, runtime_dir: str, intent_path: str, truth_files: list[str]) -> str | None:
        """
        Check whether cached context is still valid.
        Returns cached context.json content on hit, None on miss.
        """
        meta_path = Path(runtime_dir) / "context-meta.json"
        context_path = self._resolve_context_path(runtime_dir)
        if not meta_path.exists() or context_path is None:
            _log("L2:ContextReuse", "MISS", "no context-meta.json or context.json")
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            intent_hash = self._hash_file(intent_path)
            truth_hash = self._hash_files(truth_files)
            if meta.get("intentHash") == intent_hash and meta.get("truthFilesHash") == truth_hash:
                content = Path(context_path).read_text(encoding="utf-8")
                _log("L2:ContextReuse", "HIT", f"hashes match — reusing {Path(context_path).name}")
                return content
            _log("L2:ContextReuse", "MISS", "hash mismatch")
            return None
        except (OSError, json.JSONDecodeError):
            _log("L2:ContextReuse", "MISS", "failed to read or parse context-meta.json")
            return None

    def save(self, runtime_dir: str, intent_path: str, truth_files: list[str]) -> None:
        """Save context metadata after a successful prepare."""
        meta_path = Path(runtime_dir) / "context-meta.json"
        meta = {
            "intentHash": self._hash_file(intent_path),
            "truthFilesHash": self._hash_files(truth_files),
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        try:
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            _log("L2:ContextReuse", "SAVE", str(meta_path))
        except OSError:
            _log("L2:ContextReuse", "MISS", "failed to write context-meta.json")

    def invalidate(self, runtime_dir: str) -> None:
        """Delete context-meta.json in the given runtime directory."""
        meta_path = Path(runtime_dir) / "context-meta.json"
        try:
            if meta_path.exists():
                meta_path.unlink()
                _log("L2:ContextReuse", "CLEAR", str(meta_path))
        except OSError:
            pass  # best-effort cleanup

    def _resolve_context_path(self, runtime_dir: str) -> str | None:
        try:
            files = sorted(
                (
                    f.name
                    for f in Path(runtime_dir).iterdir()
                    if f.name.endswith(".context.json") and f.name.startswith("chapter-")
                ),
                reverse=True,
            )
            return str(Path(runtime_dir) / files[0]) if files else None
        except OSError:
            return None


# --- Layer 3: Lazy Loader (in-memory, per-session) ---

class LazyLoader:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def load(self, file_path: str) -> str:
        """Load file on first access; return cached content on subsequent calls."""
        if file_path in self._store:
            _log("L3:LazyLoad", "HIT", file_path)
            return self._store[file_path]
        _log("L3:LazyLoad", "MISS", file_path)
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            self._store[file_path] = content
            return content
        except OSError:
            self._store[file_path] = ""
            return ""

    def clear(self) -> None:
        size = len(self._store)
        self._store.clear()
        _log("L3:LazyLoad", "CLEAR", f"all {size} entries")

    @property
    def size(self) -> int:
        return len(self._store)


# --- Invalidation: called when any truth file is updated ---

def on_truth_file_update(
    book_id: str,
    session: SessionCache,
    books_root: str = "books",
) -> None:
    """
    Clears L1 (session cache) and deletes L2 context-meta.json.
    L3 (lazy loader) is NOT cleared — genre profiles / style guides are not truth files.
    """
    session.clear()
    _log("Invalidation", "CLEAR", f"L1 session cache cleared for book {book_id}")

    runtime_dir = str(Path(books_root) / book_id / "story" / "runtime")
    reuse = ContextReuse()
    reuse.invalidate(runtime_dir)
    _log("Invalidation", "CLEAR", f"L2 context-meta.json removed for book {book_id}")
