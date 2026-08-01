"""Persistence for role and opportunity gap analyses."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from app.database import get_db
from app.models import GapAnalysisResult

MODES = {"profile_vs_role", "profile_vs_jd", "profile_vs_opportunity"}
COLUMNS = "id, profile_id, opportunity_id, target_role, analysis_mode, overall_assessment, missing_skills, suggested_projects, evidence_data, jd_snippet, profile_snapshot, generated_at"

def _serialize_json(value: Any) -> str: return json.dumps(value, default=str)
def _deserialize_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]"); return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError): return []
def _deserialize_dict(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}"); return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError): return {}

def _utc(value: datetime | str | None) -> datetime | None:
    if isinstance(value, str):
        try: value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError: return None
    if not isinstance(value, datetime): return None
    if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def calculate_is_stale(generated_at, *, now=None, max_age_days=7) -> bool:
    generated = _utc(generated_at)
    if generated is None: return True
    current = _utc(now) or datetime.now(timezone.utc)
    return generated < current - timedelta(days=max(1, min(int(max_age_days), 365)))

def row_to_gap_analysis(row) -> dict | None:
    if row is None: return None
    item = dict(row)
    for field in ("missing_skills", "suggested_projects", "evidence_data"): item[field] = _deserialize_list(item.get(field))
    item["profile_snapshot"] = _deserialize_dict(item.get("profile_snapshot"))
    item["jd_snippet"] = (item.get("jd_snippet") or "")[:300] or None
    item["is_stale"] = calculate_is_stale(item.get("generated_at"))
    return item

async def save_gap_analysis(analysis: GapAnalysisResult | dict, *, persist: bool = True) -> dict:
    data = analysis.model_dump(mode="json") if hasattr(analysis, "model_dump") else dict(analysis)
    mode = data.get("analysis_mode")
    if mode not in MODES: raise ValueError("Unsupported analysis mode.")
    data["id"] = str(data.get("id") or uuid.uuid4())
    generated = _utc(data.get("generated_at")) or datetime.now(timezone.utc)
    data["generated_at"] = generated.isoformat()
    data["jd_snippet"] = str(data.get("jd_snippet") or "")[:300] or None
    if not persist or mode == "profile_vs_jd":
        data["is_stale"] = calculate_is_stale(generated); return data
    conflict = "profile_id" if mode == "profile_vs_role" else "profile_id, opportunity_id"
    async with get_db() as db:
        await db.execute(f"""INSERT INTO gap_analyses ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT ({conflict}) WHERE {'opportunity_id IS NULL AND analysis_mode = \'profile_vs_role\'' if mode == 'profile_vs_role' else "opportunity_id IS NOT NULL AND analysis_mode = 'profile_vs_opportunity'"}
        DO UPDATE SET id=excluded.id, target_role=excluded.target_role, overall_assessment=excluded.overall_assessment, missing_skills=excluded.missing_skills, suggested_projects=excluded.suggested_projects, evidence_data=excluded.evidence_data, jd_snippet=excluded.jd_snippet, profile_snapshot=excluded.profile_snapshot, generated_at=excluded.generated_at, updated_at=CURRENT_TIMESTAMP""",
        (data["id"], data["profile_id"], data.get("opportunity_id"), data["target_role"], mode, data["overall_assessment"], _serialize_json(data.get("missing_skills", [])), _serialize_json(data.get("suggested_projects", [])), _serialize_json(data.get("evidence_data", [])), data["jd_snippet"], _serialize_json(data.get("profile_snapshot", {})), data["generated_at"])); await db.commit()
    return await get_analysis_by_id(data["id"])

async def _one(query: str, values: tuple) -> dict | None:
    async with get_db() as db:
        cursor = await db.execute(f"SELECT {COLUMNS} FROM gap_analyses WHERE {query}", values); row = await cursor.fetchone(); await cursor.close()
    return row_to_gap_analysis(row)
async def get_analysis_by_id(analysis_id: str): return await _one("id = ?", (analysis_id,))
async def get_latest_role_analysis(profile_id: str): return await _one("profile_id = ? AND opportunity_id IS NULL AND analysis_mode = 'profile_vs_role' ORDER BY generated_at DESC LIMIT 1", (profile_id,))
async def get_opportunity_analysis(profile_id: str, opportunity_id: str): return await _one("profile_id = ? AND opportunity_id = ? AND analysis_mode = 'profile_vs_opportunity' ORDER BY generated_at DESC LIMIT 1", (profile_id, opportunity_id))
