"""Application package for the OpportunIQ backend.

Environment loading belongs at the package boundary: Python executes this file
before importing ``app.main``, ``app.config``, routers, services, or agents.
Production-injected environment variables remain authoritative.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


_project_root = Path(__file__).resolve().parent.parent
_configured_env_file = os.getenv("OPPORTUNIQ_ENV_FILE", "").strip()
_env_file = Path(_configured_env_file) if _configured_env_file else _project_root / ".env"
load_dotenv(dotenv_path=_env_file, override=False)
