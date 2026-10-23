"""SQLite persistence with per-operation connections."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .engine import Analysis


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def init(self) -> None:
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    category_label TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reasons TEXT NOT NULL,
                    handling_mode TEXT NOT NULL,
                    pii_detected INTEGER NOT NULL,
                    estimated_minutes_saved INTEGER NOT NULL,
                    provider_used TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    api_cost_usd REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new'
                )
            """)

    def create(self, analysis: Analysis, source: str = "web") -> dict:
        with self.connect() as db:
            cursor = db.execute(
                """INSERT INTO tickets (created_at, source, text, category, category_label, priority,
                owner, action, reasons, handling_mode, pii_detected, estimated_minutes_saved,
                provider_used, input_tokens, output_tokens, api_cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (utcnow(), source, analysis.masked_text, analysis.category,
                 analysis.category_label, analysis.priority, analysis.owner, analysis.action,
                 json.dumps(analysis.reasons, ensure_ascii=False), analysis.handling_mode,
                 int(analysis.pii_detected), analysis.estimated_minutes_saved,
                 analysis.provider_used, analysis.input_tokens, analysis.output_tokens,
                 analysis.api_cost_usd),
            )
            return self.get(cursor.lastrowid, db=db)

    def get(self, ticket_id: int, db: sqlite3.Connection | None = None) -> dict | None:
        if db is None:
            with self.connect() as conn:
                return self.get(ticket_id, db=conn)
        row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._record(row) if row else None

    def list(self, limit: int = 100) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [self._record(x) for x in rows]

    def update_status(self, ticket_id: int, status: str) -> dict | None:
        with self.connect() as db:
            db.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
            return self.get(ticket_id, db=db)

    def stats(self) -> dict:
        with self.connect() as db:
            row = db.execute("""
                SELECT COUNT(*) as total, SUM(priority = 'high') as urgent,
                COALESCE(SUM(estimated_minutes_saved), 0) as minutes_saved,
                COALESCE(SUM(api_cost_usd), 0) as api_cost_usd,
                COALESCE(SUM(status = 'resolved'), 0) as resolved
                FROM tickets
            """).fetchone()
            counts = db.execute("SELECT category_label, COUNT(*) AS count FROM tickets GROUP BY category_label ORDER BY count DESC").fetchall()
            return {
                "total": row["total"], "urgent": row["urgent"] or 0,
                "minutes_saved_assumption": row["minutes_saved"],
                "api_cost_usd": round(row["api_cost_usd"], 6),
                "resolved": row["resolved"],
                "categories": [{"name": x["category_label"], "count": x["count"]} for x in counts],
            }

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        item = dict(row)
        item["reasons"] = json.loads(item["reasons"])
        item["pii_detected"] = bool(item["pii_detected"])
        return item
