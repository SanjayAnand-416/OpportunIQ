"""Opt-in smoke checks for configured external integrations.

This script is intentionally excluded from pytest. Each check requires a
`LIVE_SMOKE_<SERVICE>=true` environment flag. Secrets and content are never
printed.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def enabled(service: str) -> bool:
    return os.getenv(f"LIVE_SMOKE_{service.upper()}", "false").lower() == "true"


def active_module(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


async def check_groq() -> None:
    module = active_module("app.services.groq_service")
    if module is None or not enabled("groq"):
        print("SKIP groq")
        return
    if not os.getenv("GROQ_API_KEY"):
        print("SKIP groq: credential missing")
        return
    try:
        result = await module.generate_reminder(
            profile_name="Smoke Test",
            skills=["Python"],
            deadline_title="Safe smoke-test deadline",
            deadline_datetime="2030-01-01T00:00:00+00:00",
            days_left=1,
        )
        if result is None:
            raise RuntimeError("empty result")
        print("PASS groq")
    except Exception as exc:
        print(f"FAIL groq: {type(exc).__name__}")
        raise


async def check_tavily() -> None:
    module = active_module("app.services.tavily_service")
    if module is None or not enabled("tavily"):
        print("SKIP tavily")
        return
    if not os.getenv("TAVILY_API_KEY"):
        print("SKIP tavily: credential missing")
        return
    try:
        results = await module.search_hackathons_and_portals(
            role="Software Intern", skills=["Python"], limit=1
        )
        if not isinstance(results, list):
            raise TypeError("unexpected result")
        print("PASS tavily")
    except Exception as exc:
        print(f"FAIL tavily: {type(exc).__name__}")
        raise


async def check_smtp(recipient: str | None) -> None:
    module = active_module("app.services.email_service")
    if module is None or not enabled("smtp"):
        print("SKIP smtp")
        return
    if not recipient:
        print("SKIP smtp: pass --send-email to confirm delivery")
        return
    if not os.getenv("SMTP_FROM_EMAIL") or not os.getenv("SMTP_APP_PASSWORD"):
        print("SKIP smtp: credential missing")
        return
    success = await module.send_reminder_email(
        to_email=recipient,
        subject="OpportunIQ integration smoke test",
        body="This is an explicitly requested, content-free smoke test.",
    )
    if not success:
        print("FAIL smtp: delivery returned false")
        raise RuntimeError("SMTP smoke test failed")
    print("PASS smtp")


def report_guarded_modules() -> None:
    for service, module_name in (
        ("resumeai", "app.services.resume_service"),
        ("gmail", "app.services.gmail_service"),
        ("guardian", "app.agents.guardian_agent"),
        ("gap-analysis", "app.agents.gap_analysis_agent"),
    ):
        status = "adapter available" if active_module(module_name) else "guarded missing"
        print(f"SKIP {service}: {status}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send-email",
        metavar="RECIPIENT",
        help="Explicitly confirm SMTP delivery to this address",
    )
    args = parser.parse_args()
    failures = []
    for check in (check_groq, check_tavily):
        try:
            await check()
        except Exception:
            failures.append(check.__name__)
    try:
        await check_smtp(args.send_email)
    except Exception:
        failures.append("check_smtp")
    report_guarded_modules()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
