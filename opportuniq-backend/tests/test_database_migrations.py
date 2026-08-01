"""Regression coverage for additive startup migrations."""

import asyncio
import sqlite3

from app import database


def _run_init(path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", str(path))
    asyncio.run(database.init_db())


def test_empty_database_initializes_twice(tmp_path, monkeypatch):
    path = tmp_path / "empty.sqlite"

    _run_init(path, monkeypatch)
    _run_init(path, monkeypatch)

    with sqlite3.connect(path) as connection:
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    assert table_count == 11


def test_legacy_profiles_and_opportunities_receive_stable_public_ids(
    tmp_path, monkeypatch
):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE student_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                skills TEXT
            );
            INSERT INTO student_profiles (name, email, skills)
            VALUES ('Legacy Student', 'legacy@example.com', '[]');

            CREATE TABLE opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT,
                description TEXT,
                deadline TEXT,
                opportunity_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO opportunities (source, external_id, title)
            VALUES ('legacy', 'one', 'Legacy Opportunity');
            """
        )

    _run_init(path, monkeypatch)
    with sqlite3.connect(path) as connection:
        first_profile_id = connection.execute(
            "SELECT profile_id FROM student_profiles WHERE id = 1"
        ).fetchone()[0]
        first_opportunity_id = connection.execute(
            "SELECT opportunity_id FROM opportunities WHERE id = 1"
        ).fetchone()[0]

    _run_init(path, monkeypatch)
    with sqlite3.connect(path) as connection:
        second_profile_id = connection.execute(
            "SELECT profile_id FROM student_profiles WHERE id = 1"
        ).fetchone()[0]
        second_opportunity_id = connection.execute(
            "SELECT opportunity_id FROM opportunities WHERE id = 1"
        ).fetchone()[0]

    assert first_profile_id == second_profile_id
    assert first_opportunity_id == second_opportunity_id
    assert len(first_profile_id) == len(first_opportunity_id) == 36


def test_duplicate_legacy_rows_do_not_abort_index_migration(tmp_path, monkeypatch):
    path = tmp_path / "duplicates.sqlite"
    _run_init(path, monkeypatch)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP INDEX idx_saved_profile_opportunity")
        connection.executemany(
            "INSERT INTO saved_opportunities "
            "(id, profile_id, opportunity_id) VALUES (?, 'profile', 'opportunity')",
            [("saved-one",), ("saved-two",)],
        )
        connection.commit()

    _run_init(path, monkeypatch)

    with sqlite3.connect(path) as connection:
        retained = connection.execute(
            "SELECT COUNT(*) FROM saved_opportunities "
            "WHERE profile_id = 'profile' AND opportunity_id = 'opportunity'"
        ).fetchone()[0]
        unique_index = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'index' AND name = 'idx_saved_profile_opportunity'"
        ).fetchone()[0]
    assert retained == 2
    assert unique_index == 0
