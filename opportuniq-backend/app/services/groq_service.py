"""Canonical active-package Groq reminder adapter."""

import json
import os
from pydantic import BaseModel


class ReminderMessage(BaseModel):
    subject: str
    body: str


async def generate_reminder(*, profile_name: str, skills: list[str], deadline_title: str, deadline_datetime: str, days_left: int | None) -> ReminderMessage:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    from groq import AsyncGroq
    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Return JSON with subject and body. Keep the reminder under 100 words."},
            {"role": "user", "content": f"Student: {profile_name}\nSkills: {', '.join(skills)}\nDeadline: {deadline_title}\nDue: {deadline_datetime}\nDays left: {days_left}"},
        ],
    )
    return ReminderMessage(**json.loads(response.choices[0].message.content or "{}"))
