"""SQLite baseline store for row-count delta checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class BaselineStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS row_counts (check_name TEXT PRIMARY KEY, row_count INTEGER NOT NULL)"
        )
        self._conn.commit()

    def get(self, check_name: str) -> int | None:
        row = self._conn.execute(
            "SELECT row_count FROM row_counts WHERE check_name = ?", (check_name,)
        ).fetchone()
        return None if row is None else int(row[0])

    def set(self, check_name: str, row_count: int) -> None:
        self._conn.execute(
            """
            INSERT INTO row_counts (check_name, row_count) VALUES (?, ?)
            ON CONFLICT(check_name) DO UPDATE SET row_count = excluded.row_count
            """,
            (check_name, row_count),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
