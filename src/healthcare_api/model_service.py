"""Model loading and prediction service."""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    API_VERSION,
    CLAIM_MODEL_VERSION,
    MODEL_DIR,
    PHASE3_DIR,
    PREDICTION_LOG_PATH,
    PROJECT_ROOT,
    RISK_MODEL_VERSION,
)
from .logging_utils import write_jsonl
from .schemas import ClaimPredictionRequest, PredictionResponse, RiskPredictionRequest


LOCAL_LIB = PROJECT_ROOT / ".pythonlibs"
if LOCAL_LIB.exists() and str(LOCAL_LIB) not in sys.path:
    sys.path.insert(0, str(LOCAL_LIB))

import joblib


class HealthcareModelService:
    """Loads trained models and exposes prediction helpers."""

    def __init__(self) -> None:
        self.risk_model = joblib.load(MODEL_DIR / "risk_selected_model.joblib")
        self.claim_model = joblib.load(MODEL_DIR / "claim_selected_model.joblib")
        self.risk_feature_set = self._load_feature_set("risk_feature_set.json")
        self.claim_feature_set = self._load_feature_set("claim_feature_set.json")
        self.risk_metrics = self._load_json(PHASE3_DIR / "risk_model_metrics.json")
        self.claim_metrics = self._load_json(PHASE3_DIR / "claim_model_metrics.json")

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_feature_set(self, file_name: str) -> dict[str, Any]:
        return self._load_json(PHASE3_DIR / file_name)

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> dict[str, Any]:
        canonical: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                canonical[key] = value.date().isoformat()
            else:
                canonical[key] = value
        return canonical

    @staticmethod
    def _feature_hash(features: dict[str, Any]) -> str:
        encoded = json.dumps(features, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _probabilities(model: Any, row: pd.DataFrame) -> dict[str, float]:
        probs = model.predict_proba(row)[0]
        return {
            str(label): round(float(probability), 6)
            for label, probability in zip(model.classes_, probs)
        }

    @staticmethod
    def _request_id(request_id: str | None) -> str:
        return request_id or str(uuid.uuid4())

    def metadata(self) -> dict[str, Any]:
        return {
            "api_version": API_VERSION,
            "risk_model_version": RISK_MODEL_VERSION,
            "claim_model_version": CLAIM_MODEL_VERSION,
            "risk_selected_model": self.risk_metrics["selected_model"],
            "claim_selected_model": self.claim_metrics["selected_model"],
            "risk_features": self.risk_feature_set,
            "claim_features": self.claim_feature_set,
        }

    def _predict(
        self,
        model_name: str,
        model: Any,
        model_version: str,
        feature_set: dict[str, Any],
        request_id: str | None,
        payload: dict[str, Any],
    ) -> PredictionResponse:
        features = feature_set["categorical_features"] + feature_set["numeric_features"]
        canonical = self._canonical_payload(payload)
        row = pd.DataFrame([{feature: canonical.get(feature) for feature in features}])
        for col in feature_set["categorical_features"]:
            row[col] = row[col].astype("string").fillna("Unknown")
        for col in feature_set["numeric_features"]:
            row[col] = pd.to_numeric(row[col], errors="coerce")

        prediction = str(model.predict(row)[0])
        probabilities = self._probabilities(model, row)
        feature_hash = self._feature_hash({feature: canonical.get(feature) for feature in features})
        resolved_request_id = self._request_id(request_id)
        generated_at = datetime.now(timezone.utc)

        write_jsonl(
            PREDICTION_LOG_PATH,
            {
                "request_id": resolved_request_id,
                "model_name": model_name,
                "model_version": model_version,
                "prediction": prediction,
                "probabilities": probabilities,
                "feature_hash": feature_hash,
                "api_version": API_VERSION,
            },
        )

        return PredictionResponse(
            request_id=resolved_request_id,
            model_name=model_name,
            model_version=model_version,
            prediction=prediction,
            probabilities=probabilities,
            feature_hash=feature_hash,
            logged=True,
            generated_at_utc=generated_at,
        )

    def predict_risk(self, request: RiskPredictionRequest) -> PredictionResponse:
        return self._predict(
            model_name="risk",
            model=self.risk_model,
            model_version=RISK_MODEL_VERSION,
            feature_set=self.risk_feature_set,
            request_id=request.request_id,
            payload=request.model_dump(),
        )

    def predict_claim(self, request: ClaimPredictionRequest) -> PredictionResponse:
        return self._predict(
            model_name="claim",
            model=self.claim_model,
            model_version=CLAIM_MODEL_VERSION,
            feature_set=self.claim_feature_set,
            request_id=request.request_id,
            payload=request.model_dump(),
        )


model_service = HealthcareModelService()

