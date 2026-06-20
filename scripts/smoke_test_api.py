"""Smoke-test the Phase 5 FastAPI app without starting a network server."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIB = PROJECT_ROOT / ".pythonlibs"
SRC_DIR = PROJECT_ROOT / "src"
for path in [LOCAL_LIB, SRC_DIR]:
    if path.exists():
        sys.path.insert(0, str(path))

from fastapi.testclient import TestClient

from healthcare_api.main import app
from healthcare_api.sample_payloads import CLAIM_SAMPLE, RISK_SAMPLE


def main() -> None:
    client = TestClient(app)

    health = client.get("/health")
    risk = client.post("/predict/risk", json=RISK_SAMPLE)
    claim = client.post("/predict/claim", json=CLAIM_SAMPLE)
    metadata = client.get("/version")

    for name, response in [
        ("health", health),
        ("risk", risk),
        ("claim", claim),
        ("version", metadata),
    ]:
        if response.status_code != 200:
            raise RuntimeError(f"{name} failed: {response.status_code} {response.text}")

    summary = {
        "health": health.json(),
        "risk_prediction": risk.json(),
        "claim_prediction": claim.json(),
        "version": metadata.json(),
    }
    out_path = PROJECT_ROOT / "data_outputs" / "phase5" / "api_smoke_test_response.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
