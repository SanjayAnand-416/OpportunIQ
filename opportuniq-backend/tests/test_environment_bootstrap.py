"""Verify dotenv is loaded before immutable runtime configuration imports."""

import json
import os
from pathlib import Path
import subprocess
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _configuration_from_fresh_process(env_file: Path, **environment_overrides):
    environment = os.environ.copy()
    for name in (
        "APP_TIMEZONE",
        "ENABLE_SCHEDULER",
        "EXTERNAL_HTTP_TIMEOUT_SECONDS",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "OPPORTUNIQ_ENV_FILE": str(env_file),
            **environment_overrides,
        }
    )
    script = """
import json
from app import config
from app.services import scheduler_service
print(json.dumps({
    "external_timeout": config.EXTERNAL_HTTP_TIMEOUT_SECONDS,
    "scheduler_enabled": config.ENABLE_SCHEDULER,
    "timezone": config.APP_TIMEZONE.key,
    "scheduler_observed_setting": scheduler_service.config.ENABLE_SCHEDULER,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return json.loads(completed.stdout)


def test_dotenv_precedes_config_and_scheduler_imports(tmp_path):
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "EXTERNAL_HTTP_TIMEOUT_SECONDS=47.5\n"
        "ENABLE_SCHEDULER=false\n"
        "APP_TIMEZONE=Europe/Paris\n",
        encoding="utf-8",
    )

    values = _configuration_from_fresh_process(env_file)

    assert values == {
        "external_timeout": 47.5,
        "scheduler_enabled": False,
        "timezone": "Europe/Paris",
        "scheduler_observed_setting": False,
    }


def test_production_environment_overrides_dotenv(tmp_path):
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "EXTERNAL_HTTP_TIMEOUT_SECONDS=47.5\n"
        "ENABLE_SCHEDULER=false\n"
        "APP_TIMEZONE=Europe/Paris\n",
        encoding="utf-8",
    )

    values = _configuration_from_fresh_process(
        env_file,
        EXTERNAL_HTTP_TIMEOUT_SECONDS="11",
        ENABLE_SCHEDULER="true",
        APP_TIMEZONE="UTC",
    )

    assert values == {
        "external_timeout": 11.0,
        "scheduler_enabled": True,
        "timezone": "UTC",
        "scheduler_observed_setting": True,
    }
