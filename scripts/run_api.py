"""Run the Phase 5 FastAPI service with local project dependencies."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in [PROJECT_ROOT / ".pythonlibs", PROJECT_ROOT / "src"]:
    if path.exists():
        sys.path.insert(0, str(path))

import uvicorn


def main() -> None:
    uvicorn.run(
        "healthcare_api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
