"""
Native LangGraph State Checkpointers with SQLite persistence.
Provides persistent state checkpointing across turns and server restarts.
"""
import os
import sys
import types
import sqlite3
import pickle
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
)
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("CheckpointSaver")
logger.setLevel(logging.INFO)


class SqliteSaver(MemorySaver, AbstractContextManager):
    """
    SQLite-backed LangGraph state checkpointer.
    Inherits from MemorySaver for blazing-fast state access while persisting
    every state transition, channel write, and blob to an ACID-compliant SQLite database.
    Thread-safe across asynchronous task workers and Pregel execution pools.
    """

    def __init__(self, conn: Optional[sqlite3.Connection] = None, db_path: str = "data/sessions.db"):
        super().__init__()
        self.db_path = db_path
        self._lock = threading.RLock()
        if conn is not None:
            self.conn = conn
        else:
            if db_path != ":memory:":
                parent = Path(db_path).parent
                if str(parent) and not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(db_path, check_same_thread=False)

        self._init_db()
        self._load_all()

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

    def _load_all(self) -> None:
        """Restores in-memory storage, writes, and blobs from SQLite."""
        with self._lock:
            cursor = self.conn.cursor()
            for t_id, ns, c_id, entry_blob in cursor.execute(
                "SELECT thread_id, checkpoint_ns, checkpoint_id, entry_blob FROM checkpoints"
            ):
                try:
                    self.storage[t_id][ns][c_id] = pickle.loads(entry_blob)
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint {c_id}: {e}")

            for t_id, ns, c_id, task_id, idx, write_blob in cursor.execute(
                "SELECT thread_id, checkpoint_ns, checkpoint_id, task_id, idx, write_blob FROM writes"
            ):
                try:
                    self.writes[(t_id, ns, c_id)][(task_id, idx)] = pickle.loads(write_blob)
                except Exception as e:
                    logger.warning(f"Failed to load write {task_id}: {e}")

            for t_id, ns, channel, version, blob_val in cursor.execute(
                "SELECT thread_id, checkpoint_ns, channel, version, blob_val FROM blobs"
            ):
                try:
                    self.blobs[(t_id, ns, channel, version)] = pickle.loads(blob_val)
                except Exception as e:
                    logger.warning(f"Failed to load blob {channel}: {e}")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Saves a checkpoint to in-memory state and persists immediately to SQLite."""
        res = super().put(config, checkpoint, metadata, new_versions)
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        c_id = checkpoint["id"]
        entry = self.storage[thread_id][checkpoint_ns].get(c_id)

        if entry:
            with self._lock, self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, c_id, pickle.dumps(entry))
                )
                for k, v in new_versions.items():
                    blob_val = self.blobs.get((thread_id, checkpoint_ns, k, v))
                    if blob_val:
                        self.conn.execute(
                            "INSERT OR REPLACE INTO blobs VALUES (?, ?, ?, ?, ?)",
                            (thread_id, checkpoint_ns, k, str(v), pickle.dumps(blob_val))
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
                        (thread_id, checkpoint_ns, checkpoint_id, t_id, w_idx, pickle.dumps(write_data))
                    )

    def delete_thread(self, thread_id: str) -> None:
        """Purges all checkpoints, writes, and blobs associated with a thread ID."""
        super().delete_thread(thread_id)
        with self._lock, self.conn:
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
