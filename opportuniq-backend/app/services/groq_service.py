"""Canonical active-package Groq reminder adapter."""

import importlib
import json
import os
from typing import Any
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


async def extract_opportunity(raw_result: dict[str, Any] | str) -> Any:
    """Delegate structured opportunity extraction to Person C's adapter boundary."""
    raw_text = raw_result if isinstance(raw_result, str) else json.dumps(raw_result, default=str)
    return await _person_c_groq().extract_opportunity(raw_text)


async def extract_deadline(email_text: str) -> Any:
    """Delegate structured Gmail deadline extraction to Person C."""
    return await _person_c_groq().extract_deadline(email_text)


async def extract_jd_skills(job_description: str) -> dict[str, Any]:
    """Delegate structured JD skill extraction to Person C."""
    return await _person_c_groq().extract_jd_skills(job_description)


async def run_gap_analysis_llm(payload: dict[str, Any]) -> dict[str, Any]:
    """Delegate validated Gap Analysis synthesis to Person C."""
    return await _person_c_groq().run_gap_analysis_llm(payload)


def _person_c_groq() -> Any:
    """Resolve the legacy implementation only at the adapter boundary."""
    return importlib.import_module("services.groq_service")
