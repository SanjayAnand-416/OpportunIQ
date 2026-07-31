import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite


DATABASE_PATH = os.getenv("DATABASE_PATH", "opportuniq.db")


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield a SQLite connection configured for dictionary-like rows."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """Initialize the SQLite database schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT UNIQUE,
                name TEXT,
                email TEXT,
                year_of_study TEXT,
                graduation_year INTEGER,
                degree TEXT,
                college TEXT,
                target_roles TEXT,
                phone TEXT,
                education TEXT,
                skills TEXT,
                location TEXT,
                opportunity_type TEXT,
                experience TEXT,
                projects TEXT,
                raw_resume_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "profile_id": "TEXT UNIQUE",
            "year_of_study": "TEXT",
            "graduation_year": "INTEGER",
            "degree": "TEXT",
            "college": "TEXT",
            "target_roles": "TEXT",
            "location": "TEXT",
            "opportunity_type": "TEXT",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE student_profiles ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT UNIQUE,
                session_id TEXT,
                profile_id TEXT,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                company TEXT,
                platform TEXT,
                organization TEXT,
                location TEXT,
                url TEXT,
                url_hash TEXT,
                description TEXT,
                deadline TEXT,
                stipend_or_prize TEXT,
                eligibility TEXT,
                skills_required TEXT,
                also_on TEXT,
                match_score REAL DEFAULT 0,
                urgency_score REAL DEFAULT 0,
                combined_score REAL DEFAULT 0,
                is_expired INTEGER DEFAULT 0,
                opportunity_type TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, external_id)
            )
            """
        )
        for column_name, column_type in {
            "opportunity_id": "TEXT UNIQUE",
            "session_id": "TEXT",
            "profile_id": "TEXT",
            "company": "TEXT",
            "platform": "TEXT",
            "url_hash": "TEXT",
            "stipend_or_prize": "TEXT",
            "eligibility": "TEXT",
            "skills_required": "TEXT",
            "also_on": "TEXT",
            "match_score": "REAL DEFAULT 0",
            "urgency_score": "REAL DEFAULT 0",
            "combined_score": "REAL DEFAULT 0",
            "is_expired": "INTEGER DEFAULT 0",
            "fetched_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE opportunities ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_session_id
            ON opportunities(session_id)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_profile_id
            ON opportunities(profile_id)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_fetched_at
            ON opportunities(fetched_at)
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                deadline_at TEXT,
                context TEXT,
                email_message_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deadline_id INTEGER,
                channel TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_for TEXT,
                sent_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(deadline_id) REFERENCES deadlines(id)
            )
            """
        )
        await db.commit()
