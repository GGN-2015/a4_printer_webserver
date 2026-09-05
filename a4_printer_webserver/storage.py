"""Persistent print-job storage."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL DEFAULT 'document',
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    media_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    queued_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS jobs_status_order
                    ON jobs(status, queued_at, created_at);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "kind" not in columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN kind TEXT NOT NULL "
                    "DEFAULT 'document'"
                )

    def recover_interrupted_jobs(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'failed', completed_at = ?,
                    error = 'The server stopped while this job was being submitted.'
                WHERE status = 'printing'
                """,
                (utc_now(),),
            )
            return cursor.rowcount

    def create_job(
        self,
        *,
        job_id: str,
        original_name: str,
        stored_name: str,
        media_type: str,
        size: int,
    ) -> dict[str, Any]:
        created_at = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, kind, original_name, stored_name, media_type, size,
                    status, created_at
                ) VALUES (?, 'document', ?, ?, ?, ?, 'uploaded', ?)
                """,
                (job_id, original_name, stored_name, media_type, size, created_at),
            )
        job = self.get_job(job_id)
        assert job is not None
        return job

    def create_test_page_job(self, *, job_id: str) -> dict[str, Any]:
        created_at = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, kind, original_name, stored_name, media_type, size,
                    status, created_at, queued_at
                ) VALUES (?, 'test_page', 'Printer test page', ?,
                    'application/pdf', 0, 'queued', ?, ?)
                """,
                (job_id, f"{job_id}.test-page", created_at, created_at),
            )
        job = self.get_job(job_id)
        assert job is not None
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                ORDER BY
                    CASE status
                        WHEN 'printing' THEN 0
                        WHEN 'queued' THEN 1
                        WHEN 'uploaded' THEN 2
                        ELSE 3
                    END,
                    CASE WHEN status IN ('printing', 'queued', 'uploaded')
                        THEN COALESCE(queued_at, created_at)
                    END ASC,
                    CASE WHEN status IN ('completed', 'failed', 'canceled')
                        THEN completed_at
                    END DESC,
                    created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_completed_documents_before(
        self, cutoff: str
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE kind = 'document'
                    AND status = 'completed'
                    AND completed_at IS NOT NULL
                    AND completed_at < ?
                ORDER BY completed_at ASC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(row) for row in rows]

    def queue_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs SET status = 'queued', queued_at = ?, error = NULL
                WHERE id = ? AND status = 'uploaded'
                """,
                (utc_now(), job_id),
            )
        return self.get_job(job_id) if cursor.rowcount else None

    def cancel_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs SET status = 'canceled', completed_at = ?
                WHERE id = ? AND status IN ('uploaded', 'queued')
                """,
                (utc_now(), job_id),
            )
        return self.get_job(job_id) if cursor.rowcount else None

    def claim_next_job(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM jobs WHERE status = 'queued'
                ORDER BY queued_at ASC, created_at ASC LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            started_at = utc_now()
            cursor = connection.execute(
                """
                UPDATE jobs SET status = 'printing', started_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (started_at, row["id"]),
            )
        return self.get_job(row["id"]) if cursor.rowcount else None

    def finish_job(self, job_id: str, error: str | None = None) -> None:
        status = "failed" if error else "completed"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, completed_at = ?, error = ?
                WHERE id = ? AND status = 'printing'
                """,
                (status, utc_now(), error, job_id),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
