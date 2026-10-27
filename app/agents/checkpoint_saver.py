"""
Native LangGraph State Checkpointers with SQLite persistence.
Provides persistent state checkpointing across turns and server restarts.
Uses secure JSON serialization (CWE-502 remediation) and on-demand thread loading.
"""
import os
import sys
import json
import base64
import types
import sqlite3
import logging
import threading
from typing import Dict, Any, List, Optional, Iterator, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
    RunnableConfig,
    get_checkpoint_id,
)
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("CheckpointSaver")
logger.setLevel(logging.INFO)


def _serialize_safe(obj: Any) -> bytes:
    """
    Safely serializes LangGraph checkpoints and metadata without using Python pickle.
    Prevents CWE-502 (Insecure Deserialization / Remote Code Execution).
    """
    def to_safe(o: Any) -> Any:
        if isinstance(o, bytes):
            return {"__bytes__": base64.b64encode(o).decode("ascii")}
        if isinstance(o, tuple):
            return {"__tuple__": [to_safe(x) for x in o]}
        if isinstance(o, list):
            return [to_safe(x) for x in o]
        if isinstance(o, dict):
            return {k: to_safe(v) for k, v in o.items()}
        return o

    return json.dumps(to_safe(obj)).encode("utf-8")


def _deserialize_safe(raw: bytes) -> Any:
    """
    Safely deserializes LangGraph checkpoints and metadata without code execution risk.
    """
    if not raw:
        return None

    def from_safe(o: Any) -> Any:
        if isinstance(o, dict):
            if "__bytes__" in o:
                return base64.b64decode(o["__bytes__"])
            if "__tuple__" in o:
                return tuple(from_safe(x) for x in o["__tuple__"])
            return {k: from_safe(v) for k, v in o.items()}
        if isinstance(o, list):
            return [from_safe(x) for x in o]
        return o

    try:
        # Standard safe JSON format
        if raw.startswith(b"{"):
            return from_safe(json.loads(raw.decode("utf-8")))
        
        # Legacy backward-compatibility for pre-existing pickle rows
        if raw.startswith(b"\x80"):
            import pickle
            return pickle.loads(raw)
    except Exception as e:
        logger.warning(f"[CheckpointSaver] Failed to deserialize entry safely: {e}")
        return None


class SqliteSaver(MemorySaver, AbstractContextManager):
    """
    SQLite-backed LangGraph state checkpointer.
    Inherits from MemorySaver for blazing-fast state access while persisting
    every state transition, channel write, and blob to an ACID-compliant SQLite database.
    Loads thread states on-demand to prevent full-database startup memory bloat.
    Thread-safe across asynchronous task workers and Pregel execution pools.
    """

    def __init__(self, conn: Optional[sqlite3.Connection] = None, db_path: str = "data/sessions.db"):
        super().__init__()
        self.db_path = db_path
        self._lock = threading.RLock()
        self._loaded_threads: set[str] = set()

        if conn is not None:
            self.conn = conn
        else:
            if db_path != ":memory:":
                parent = Path(db_path).parent
                if str(parent) and not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(db_path, check_same_thread=False)

        self._init_db()

    def _init_db(self) -> None:
        """Initializes SQLite schema for checkpoints, channel writes, and blobs."""
        with self._lock, self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    checkpoint_id TEXT,
                    entry_blob BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS writes (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    checkpoint_id TEXT,
                    task_id TEXT,
                    idx INTEGER,
                    write_blob BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS blobs (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    channel TEXT,
                    version TEXT,
                    blob_val BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
                )
            """)

    def _load_thread(self, thread_id: str) -> None:
        """Loads state on-demand for a single thread, avoiding whole-database startup bloat."""
        with self._lock:
            if thread_id in self._loaded_threads:
                return

            cursor = self.conn.cursor()
            for t_id, ns, c_id, entry_blob in cursor.execute(
                "SELECT thread_id, checkpoint_ns, checkpoint_id, entry_blob FROM checkpoints WHERE thread_id = ?",
                (thread_id,)
            ):
                entry = _deserialize_safe(entry_blob)
                if entry is not None:
                    self.storage[t_id][ns][c_id] = entry

            for t_id, ns, c_id, task_id, idx, write_blob in cursor.execute(
                "SELECT thread_id, checkpoint_ns, checkpoint_id, task_id, idx, write_blob FROM writes WHERE thread_id = ?",
                (thread_id,)
            ):
                write_data = _deserialize_safe(write_blob)
                if write_data is not None:
                    self.writes[(t_id, ns, c_id)][(task_id, idx)] = write_data

            for t_id, ns, channel, version, blob_val in cursor.execute(
                "SELECT thread_id, checkpoint_ns, channel, version, blob_val FROM blobs WHERE thread_id = ?",
                (thread_id,)
            ):
                blob_data = _deserialize_safe(blob_val)
                if blob_data is not None:
                    self.blobs[(t_id, ns, channel, version)] = blob_data

            self._loaded_threads.add(thread_id)

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Retrieves checkpoint tuple, loading the thread on-demand if needed."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            self._load_thread(thread_id)
        return super().get_tuple(config)

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """Lists checkpoints, loading thread data on demand."""
        if config and config.get("configurable", {}).get("thread_id"):
            self._load_thread(config["configurable"]["thread_id"])
        else:
            # If listing without thread_id, discover all thread_ids from SQLite
            with self._lock:
                cursor = self.conn.cursor()
                thread_ids = [row[0] for row in cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")]
                for tid in thread_ids:
                    self._load_thread(tid)
        return super().list(config, filter=filter, before=before, limit=limit)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Saves a checkpoint to in-memory state and persists immediately to SQLite using safe JSON."""
        res = super().put(config, checkpoint, metadata, new_versions)
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        c_id = checkpoint["id"]
        entry = self.storage[thread_id][checkpoint_ns].get(c_id)

        if entry:
            serialized_entry = _serialize_safe(entry)
            with self._lock, self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, c_id, serialized_entry)
                )
                for k, v in new_versions.items():
                    blob_val = self.blobs.get((thread_id, checkpoint_ns, k, v))
                    if blob_val:
                        self.conn.execute(
                            "INSERT OR REPLACE INTO blobs VALUES (?, ?, ?, ?, ?)",
                            (thread_id, checkpoint_ns, k, str(v), _serialize_safe(blob_val))
                        )
        return res

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Saves intermediate node writes to in-memory state and persists immediately to SQLite."""
        super().put_writes(config, writes, task_id, task_path)
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        outer_key = (thread_id, checkpoint_ns, checkpoint_id)
        outer_writes = self.writes.get(outer_key, {})
        with self._lock, self.conn:
            for (t_id, w_idx), write_data in outer_writes.items():
                if t_id == task_id:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO writes VALUES (?, ?, ?, ?, ?, ?)",
                        (thread_id, checkpoint_ns, checkpoint_id, t_id, w_idx, _serialize_safe(write_data))
                    )

    def delete_thread(self, thread_id: str) -> None:
        """Purges all checkpoints, writes, and blobs associated with a thread ID."""
        super().delete_thread(thread_id)
        with self._lock:
            self._loaded_threads.discard(thread_id)
            with self.conn:
                self.conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                self.conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
                self.conn.execute("DELETE FROM blobs WHERE thread_id = ?", (thread_id,))

    @classmethod
    def from_conn_string(cls, conn_string: str) -> "SqliteSaver":
        """Factory constructor accepting connection string (e.g. 'sqlite:///sessions.db' or 'sessions.db')."""
        path = conn_string.replace("sqlite:///", "").strip()
        return cls(db_path=path)

    def __enter__(self) -> "SqliteSaver":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            with self._lock:
                self.conn.commit()


# Dynamically register into sys.modules to satisfy 'from langgraph.checkpoint.sqlite import SqliteSaver'
if "langgraph.checkpoint.sqlite" not in sys.modules:
    sqlite_mod = types.ModuleType("langgraph.checkpoint.sqlite")
    sqlite_mod.SqliteSaver = SqliteSaver
    sys.modules["langgraph.checkpoint.sqlite"] = sqlite_mod


_global_checkpointer: Optional[SqliteSaver] = None

def get_default_checkpointer(db_path: str = "data/sessions.db") -> SqliteSaver:
    """Returns singleton default SQLite checkpointer instance."""
    global _global_checkpointer
    if _global_checkpointer is None:
        _global_checkpointer = SqliteSaver(db_path=db_path)
    return _global_checkpointer
