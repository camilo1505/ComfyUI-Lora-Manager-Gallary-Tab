import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from ..utils.cache_paths import CacheType, resolve_cache_path_with_migration

logger = logging.getLogger(__name__)

_OUTPUT_COLUMNS = (
    "relative_path",
    "filename",
    "file_path",
    "folder",
    "size",
    "created_at",
    "mtime",
    "sampler",
    "cfg",
    "steps",
    "seed",
    "checkpoint",
    "resolution",
    "prompt",
    "negative_prompt",
    "has_metadata",
    "sha256",
)

_OUTPUT_COLUMNS_SQL = ", ".join(_OUTPUT_COLUMNS)
_OUTPUT_PLACEHOLDERS = ", ".join("?" for _ in _OUTPUT_COLUMNS)
_OUTPUT_UPDATE_SQL = ", ".join(f"{col}=excluded.{col}" for col in _OUTPUT_COLUMNS)


class OutputsCacheService:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or resolve_cache_path_with_migration(CacheType.OUTPUT)
        self._db_lock = threading.Lock()
        self._schema_initialized = False
        try:
            directory = os.path.dirname(self._db_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create cache directory %s: %s", directory, exc)
        self._initialize_schema()

    @classmethod
    def get_instance(cls) -> "OutputsCacheService":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _connect(self, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _initialize_schema(self):
        if self._schema_initialized:
            return
        try:
            with self._db_lock:
                conn = self._connect()
                try:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS outputs (
                            relative_path TEXT PRIMARY KEY,
                            filename TEXT NOT NULL,
                            file_path TEXT NOT NULL,
                            folder TEXT DEFAULT '',
                            size INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT '',
                            mtime REAL DEFAULT 0,
                            sampler TEXT DEFAULT '',
                            cfg REAL DEFAULT NULL,
                            steps INTEGER DEFAULT NULL,
                            seed INTEGER DEFAULT NULL,
                            checkpoint TEXT DEFAULT '',
                            resolution TEXT DEFAULT '',
                            prompt TEXT DEFAULT '',
                            negative_prompt TEXT DEFAULT '',
                            has_metadata INTEGER DEFAULT 0,
                            sha256 TEXT DEFAULT ''
                        )
                        """
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_outputs_folder ON outputs(folder)"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_outputs_created_at ON outputs(created_at)"
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_outputs_filename ON outputs(filename)"
                    )
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS cache_metadata (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                        """
                    )
                    conn.commit()
                    self._schema_initialized = True
                finally:
                    conn.close()
        except Exception as exc:
            logger.warning("Failed to initialize output cache schema: %s", exc)

    def get_folder_tree(self) -> Dict[str, dict]:
        try:
            with self._db_lock:
                conn = self._connect(readonly=True)
                try:
                    rows = conn.execute(
                        "SELECT DISTINCT folder FROM outputs WHERE folder != '' ORDER BY folder"
                    ).fetchall()
                finally:
                    conn.close()
            tree = {}
            for row in rows:
                folder = row["folder"]
                parts = folder.split("/")
                node = tree
                for part in parts:
                    if part not in node:
                        node[part] = {}
                    node = node[part]
            return tree
        except Exception as exc:
            logger.warning("Failed to get folder tree from cache: %s", exc)
            return {}

    def get_cached_outputs(
        self,
        folder: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Dict], int, List[str]]:
        try:
            with self._db_lock:
                conn = self._connect(readonly=True)
                try:
                    count_query = "SELECT COUNT(*) FROM outputs"
                    query = f"SELECT {_OUTPUT_COLUMNS_SQL} FROM outputs"
                    params: List = []
                    conditions: List[str] = []
                    folders_query = "SELECT DISTINCT folder FROM outputs WHERE folder != '' ORDER BY folder"

                    if folder:
                        prefix = folder.rstrip("/") + "/"
                        conditions.append("(folder = ? OR folder LIKE ?)")
                        params.append(folder)
                        params.append(prefix + "%")
                        folders_query = (
                            "SELECT DISTINCT folder FROM outputs "
                            "WHERE folder != '' AND (folder = ? OR folder LIKE ?) "
                            "ORDER BY folder"
                        )
                        folder_params = [folder, prefix + "%"]
                    else:
                        folder_params = []

                    if conditions:
                        where = " WHERE " + " AND ".join(conditions)
                        count_query += where
                        query += where

                    sort_col = "created_at" if sort == "created_at" else "filename"
                    sort_dir = "DESC" if order == "desc" else "ASC"
                    query += f" ORDER BY {sort_col} {sort_dir}"
                    query += " LIMIT ? OFFSET ?"

                    offset = (page - 1) * page_size
                    count_params = list(params)
                    query_params = list(params) + [page_size, offset]

                    total = conn.execute(count_query, count_params).fetchone()[0]
                    rows = conn.execute(query, query_params).fetchall()

                    if isinstance(folders_query, str):
                        folder_rows = conn.execute(folders_query, folder_params).fetchall()
                    else:
                        folder_rows = conn.execute(folders_query).fetchall()

                finally:
                    conn.close()

            folders_list = sorted(
                set(row["folder"] for row in folder_rows)
            )

            items = []
            stale_paths = []
            for row in rows:
                d = dict(row)
                if not os.path.exists(d["file_path"]):
                    stale_paths.append(d["relative_path"])
                    total -= 1
                    continue
                d["has_metadata"] = bool(d["has_metadata"])
                items.append(d)

            if stale_paths:
                self._delete_batch(stale_paths)

            return items, total, folders_list

        except Exception as exc:
            logger.warning("Failed to read output cache: %s", exc)
            return [], 0, []

    def _delete_batch(self, relative_paths: List[str]):
        if not relative_paths:
            return
        try:
            with self._db_lock:
                conn = self._connect()
                try:
                    placeholders = ", ".join("?" for _ in relative_paths)
                    conn.execute(
                        f"DELETE FROM outputs WHERE relative_path IN ({placeholders})",
                        relative_paths,
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            logger.warning("Failed to delete stale cache entries: %s", exc)

    def delete_by_path(self, relative_path: str) -> bool:
        try:
            with self._db_lock:
                conn = self._connect()
                try:
                    cur = conn.execute(
                        "DELETE FROM outputs WHERE relative_path = ?", (relative_path,)
                    )
                    conn.commit()
                    return cur.rowcount > 0
                finally:
                    conn.close()
        except Exception as exc:
            logger.warning("Failed to delete cache entry %s: %s", relative_path, exc)
            return False

    def cache_outputs(self, outputs: List[Dict]):
        if not outputs:
            return
        try:
            with self._db_lock:
                conn = self._connect()
                try:
                    conn.executemany(
                        f"""
                        INSERT INTO outputs ({_OUTPUT_COLUMNS_SQL})
                        VALUES ({_OUTPUT_PLACEHOLDERS})
                        ON CONFLICT(relative_path) DO UPDATE SET {_OUTPUT_UPDATE_SQL}
                        """,
                        [
                            (
                                o["relative_path"],
                                o["filename"],
                                o["file_path"],
                                o.get("folder", ""),
                                o.get("size", 0),
                                o.get("created_at", ""),
                                o.get("mtime", 0.0),
                                o.get("sampler", ""),
                                o.get("cfg"),
                                o.get("steps"),
                                o.get("seed"),
                                o.get("checkpoint", ""),
                                o.get("resolution", ""),
                                o.get("prompt", ""),
                                o.get("negative_prompt", ""),
                                1 if o.get("has_metadata") else 0,
                                o.get("sha256", ""),
                            )
                            for o in outputs
                        ],
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            logger.warning("Failed to cache outputs: %s", exc)

    def get_output_detail(self, relative_path: str) -> Optional[Dict]:
        try:
            with self._db_lock:
                conn = self._connect(readonly=True)
                try:
                    row = conn.execute(
                        f"SELECT {_OUTPUT_COLUMNS_SQL} FROM outputs WHERE relative_path = ?",
                        (relative_path,),
                    ).fetchone()
                finally:
                    conn.close()
            if row:
                d = dict(row)
                d["has_metadata"] = bool(d["has_metadata"])
                return d
            return None
        except Exception as exc:
            logger.warning("Failed to get output detail: %s", exc)
            return None

    def invalidate_all(self):
        try:
            with self._db_lock:
                conn = self._connect()
                try:
                    conn.execute("DELETE FROM outputs")
                    conn.commit()
                finally:
                    conn.close()
            logger.info("Output cache invalidated")
        except Exception as exc:
            logger.warning("Failed to invalidate output cache: %s", exc)

    def get_cache_entries(self, relative_paths: List[str]) -> Dict[str, dict]:
        if not relative_paths:
            return {}
        try:
            with self._db_lock:
                conn = self._connect(readonly=True)
                try:
                    placeholders = ", ".join("?" for _ in relative_paths)
                    rows = conn.execute(
                        f"SELECT {_OUTPUT_COLUMNS_SQL} FROM outputs WHERE relative_path IN ({placeholders})",
                        relative_paths,
                    ).fetchall()
                    return {row["relative_path"]: dict(row) for row in rows}
                finally:
                    conn.close()
        except Exception as exc:
            logger.warning("Failed to get cache entries: %s", exc)
            return {}

    def is_cache_populated(self) -> bool:
        try:
            with self._db_lock:
                conn = self._connect(readonly=True)
                try:
                    count = conn.execute("SELECT COUNT(*) FROM outputs").fetchone()[0]
                    return count > 0
                finally:
                    conn.close()
        except Exception:
            return False
