"""Caché local (SQLite) de resultados de matching Amazon -> CJdropshipping.

Evita volver a consultar la API de CJ / Claude para el mismo producto en
ejecuciones sucesivas durante el desarrollo.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from common.config import settings
from common.logging_conf import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS matching_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


class MatchingCache:
    def __init__(self, path: Optional[str] = None):
        self.path = path or settings.cache_path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def get(self, key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT value FROM matching_cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        logger.info("Cache HIT para key=%s", key)
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO matching_cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        self._conn.commit()
        logger.info("Cache SET para key=%s", key)

    def close(self) -> None:
        self._conn.close()
