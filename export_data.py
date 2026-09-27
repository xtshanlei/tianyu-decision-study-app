"""Researcher-only export of the persistent study database."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

from storage import _engine_url


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set DATABASE_URL before exporting study data.")
    output_dir = Path(os.environ.get("EXPORT_DIR", "exports"))
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(_engine_url(database_url), pool_pre_ping=True)

    queries = {
        "participants.csv": "SELECT * FROM participants ORDER BY created_at, id",
        "analysis.csv": """SELECT p.id AS participant_id, p.participation_id,
            p.condition, p.choice,
            p.reason, p.prompt_sha256, p.model, p.created_at AS participant_created_at,
            p.completed_at AS participant_completed_at, t.turn_index, t.question,
            t.answer, t.word_count, t.completed_at AS turn_completed_at
            FROM participants AS p LEFT JOIN turns AS t ON t.participant_id = p.id
            ORDER BY p.created_at, p.id, t.turn_index""",
        "attempts.csv": "SELECT * FROM attempts ORDER BY started_at, id",
    }
    with engine.connect() as connection:
        for filename, query in queries.items():
            result = connection.execute(text(query))
            columns = list(result.keys())
            rows = result.mappings().all()
            with (output_dir / filename).open(
                "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(file, fieldnames=columns)
                writer.writeheader()
                writer.writerows(dict(row) for row in rows)

        attempts = connection.execute(
            text("SELECT * FROM attempts ORDER BY started_at, id")
        ).mappings()
        with (output_dir / "attempts.jsonl").open("w", encoding="utf-8") as file:
            for row in attempts:
                file.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
    print(f"Study data exported to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
