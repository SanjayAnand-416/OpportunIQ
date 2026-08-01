import asyncio
from app.services import skill_gap_service

def test_exact_partial_missing_and_percentage(monkeypatch):
    scores = {("machine learning", "ml"): .8}
    monkeypatch.setattr(skill_gap_service, "cosine_score", lambda a,b: scores.get((a,b), 0.1))
    result = asyncio.run(skill_gap_service.calculate_skill_gap(opportunity={"skills_required":[" Python ", "machine learning", "Docker", "python"]}, profile={"skills":["PYTHON", "ml"]}))
    assert result["matched"] == ["python"]
    assert result["partial"][0]["matched_as"] == "ml"
    assert result["missing"] == ["Docker"]
    assert result["match_percentage"] == 60.0

def test_empty_skill_edges(monkeypatch):
    assert asyncio.run(skill_gap_service.calculate_skill_gap(opportunity={"skills_required":[]}, profile={"skills":[]}))["match_percentage"] == 100
    result = asyncio.run(skill_gap_service.calculate_skill_gap(opportunity={"skills_required":["AWS"]}, profile={"skills":[]}))
    assert result["missing"] == ["AWS"] and result["match_percentage"] == 0

def test_lazy_model_reuse(monkeypatch):
    marker = object(); skill_gap_service._model = marker
    assert skill_gap_service.get_embedding_model() is marker
