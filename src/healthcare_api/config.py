"""Runtime configuration for the Healthcare Risk Intelligence API."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models"
DATA_OUTPUTS_DIR = PROJECT_ROOT / "data_outputs"
PHASE3_DIR = DATA_OUTPUTS_DIR / "phase3"
PHASE4_DIR = DATA_OUTPUTS_DIR / "phase4"
LOG_DIR = PROJECT_ROOT / "logs"
PREDICTION_LOG_PATH = LOG_DIR / "prediction_audit_log.jsonl"

API_VERSION = "1.0.0"
RISK_MODEL_VERSION = "risk-v1.0.0-phase3"
CLAIM_MODEL_VERSION = "claim-v1.0.0-phase3"

