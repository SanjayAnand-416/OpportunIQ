import asyncio

from app.services import jobspy_service


class FakeDataFrame:
    def __init__(self, records):
        self._records = records
        self.empty = not records

    def to_dict(self, orient):
        assert orient == "records"
        return self._records


def test_normal_dataframe_result_becomes_dicts(monkeypatch):
    def fake_scrape_jobs(**kwargs):
        return FakeDataFrame(
            [
                {
                    "title": "ML Intern",
                    "company": "Acme",
                    "job_url": "https://example.com/job",
                    "site": "linkedin",
                }
            ]
        )

    monkeypatch.setattr(jobspy_service, "scrape_jobs", fake_scrape_jobs)

    results = asyncio.run(jobspy_service.search_jobs("ML Intern", "Chennai", "Internship"))

    assert results[0]["url"] == "https://example.com/job"
    assert results[0]["source"] == "jobspy"
    assert results[0]["platform"] == "linkedin"


def test_nan_becomes_none():
    result = jobspy_service.normalize_jobspy_record({"title": float("nan")})

    assert result["title"] is None


def test_empty_dataframe_returns_empty_list(monkeypatch):
    monkeypatch.setattr(jobspy_service, "scrape_jobs", lambda **kwargs: FakeDataFrame([]))

    assert asyncio.run(jobspy_service.search_jobs("Data Analyst", None, None)) == []


def test_blank_role_returns_empty_list(monkeypatch):
    called = False

    def fake_scrape_jobs(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(jobspy_service, "scrape_jobs", fake_scrape_jobs)

    assert asyncio.run(jobspy_service.search_jobs(" ", None, None)) == []
    assert called is False


def test_scrape_exception_returns_empty_list(monkeypatch):
    def fake_scrape_jobs(**kwargs):
        raise RuntimeError("network failed")

    monkeypatch.setattr(jobspy_service, "scrape_jobs", fake_scrape_jobs)

    assert asyncio.run(jobspy_service.search_jobs("ML Intern", None, None)) == []


def test_timeout_returns_empty_list(monkeypatch):
    def fake_to_thread(function, **kwargs):
        return object()

    async def fake_wait_for(awaitable, timeout):
        raise asyncio.TimeoutError

    monkeypatch.setattr(jobspy_service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(jobspy_service.asyncio, "wait_for", fake_wait_for)

    assert asyncio.run(jobspy_service.search_jobs("ML Intern", None, None)) == []


def test_results_wanted_cap(monkeypatch):
    captured = {}

    def fake_scrape_jobs(**kwargs):
        captured.update(kwargs)
        return FakeDataFrame([])

    monkeypatch.setattr(jobspy_service, "scrape_jobs", fake_scrape_jobs)

    asyncio.run(jobspy_service.search_jobs("ML Intern", None, None, results_wanted=999))

    assert captured["results_wanted"] == jobspy_service.MAX_RESULTS_WANTED


def test_scrape_uses_to_thread(monkeypatch):
    called = False

    async def fake_to_thread(function, **kwargs):
        nonlocal called
        called = True
        return FakeDataFrame([])

    monkeypatch.setattr(jobspy_service.asyncio, "to_thread", fake_to_thread)

    asyncio.run(jobspy_service.search_jobs("ML Intern", None, None))

    assert called is True
