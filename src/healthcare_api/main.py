"""FastAPI app for hospital operations and revenue risk predictions."""

from __future__ import annotations

from fastapi import FastAPI

from .config import API_VERSION, CLAIM_MODEL_VERSION, PREDICTION_LOG_PATH, RISK_MODEL_VERSION
from .model_service import model_service
from .schemas import (
    ApiMetadata,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ClaimPredictionRequest,
    HealthResponse,
    PredictionResponse,
    RiskPredictionRequest,
    utc_now,
)


app = FastAPI(
    title="Healthcare Operations & Revenue Risk Intelligence API",
    version=API_VERSION,
    description=(
        "Real-time prediction API for visit risk classification and insurance "
        "claim outcome classification."
    ),
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        api_version=API_VERSION,
        models_loaded={"risk": model_service.risk_model is not None, "claim": model_service.claim_model is not None},
        log_path=str(PREDICTION_LOG_PATH),
        checked_at_utc=utc_now(),
    )


@app.get("/metadata", tags=["system"])
def metadata() -> dict:
    return model_service.metadata()


@app.post("/predict/risk", response_model=PredictionResponse, tags=["predictions"])
def predict_risk(request: RiskPredictionRequest) -> PredictionResponse:
    return model_service.predict_risk(request)


@app.post("/predict/claim", response_model=PredictionResponse, tags=["predictions"])
def predict_claim(request: ClaimPredictionRequest) -> PredictionResponse:
    return model_service.predict_claim(request)


@app.post("/predict/batch", response_model=BatchPredictionResponse, tags=["predictions"])
def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    return BatchPredictionResponse(
        risk_predictions=[model_service.predict_risk(item) for item in request.risk_requests],
        claim_predictions=[model_service.predict_claim(item) for item in request.claim_requests],
        generated_at_utc=utc_now(),
    )


@app.get("/version", response_model=ApiMetadata, tags=["system"])
def version() -> ApiMetadata:
    return ApiMetadata(
        api_version=API_VERSION,
        risk_model_version=RISK_MODEL_VERSION,
        claim_model_version=CLAIM_MODEL_VERSION,
        model_loaded={"risk": model_service.risk_model is not None, "claim": model_service.claim_model is not None},
        generated_at_utc=utc_now(),
    )

