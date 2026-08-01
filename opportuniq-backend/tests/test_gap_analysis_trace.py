import asyncio
from app.routers import gap_analysis

def test_guard_caps_resources_and_projects():
    from app.models import GapAnalysisResult
    from datetime import datetime,timezone
    missing=[{"skill":str(i),"priority":"high","reason":"r","evidence_level":0,"learning_path_order":i,"learning_resources":[{"resource":"bad","url":"javascript:x"},{"resource":"ok","url":"https://x.test"}]} for i in range(10)]
    value=GapAnalysisResult(id="a",profile_id="p",target_role="r",analysis_mode="profile_vs_role",overall_assessment="A sufficiently detailed assessment.",missing_skills=missing,suggested_projects=[{"project_type":"x","description":"d"}]*5,generated_at=datetime.now(timezone.utc))
    guarded=gap_analysis._guard_result(value,None)
    assert len(guarded.missing_skills)==8 and len(guarded.suggested_projects)==3
    assert len(guarded.missing_skills[0].learning_resources)==1
