import os

import aiosqlite


DATABASE_PATH = os.getenv("DATABASE_PATH", "opportuniq.db")


async def init_db() -> None:
    """Initialize the SQLite database schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                education TEXT,
                skills TEXT,
                experience TEXT,
                projects TEXT,
                raw_resume_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                organization TEXT,
                location TEXT,
                url TEXT,
                description TEXT,
                deadline TEXT,
                opportunity_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, external_id)
            )
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
