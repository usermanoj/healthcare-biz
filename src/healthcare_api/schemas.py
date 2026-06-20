"""Pydantic request and response schemas for prediction endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


Gender = Literal["M", "F"]
City = Literal["Hyderabad", "Bangalore", "Delhi", "Pune", "Mumbai", "Chennai"]
InsuranceProvider = Literal["MediCareX", "CareOne", "HealthPlus", "SecureLife"]
Department = Literal["General", "ER", "Neurology", "Orthopedics", "Cardiology", "ICU"]
VisitType = Literal["OPD", "ER", "ICU"]


class ApiMetadata(BaseModel):
    api_version: str
    risk_model_version: str
    claim_model_version: str
    model_loaded: dict[str, bool]
    generated_at_utc: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    api_version: str
    models_loaded: dict[str, bool]
    log_path: str
    checked_at_utc: datetime


class BasePredictionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    age: int = Field(..., ge=0, le=120)
    gender: Gender
    city: City
    insurance_provider: InsuranceProvider
    chronic_flag: int = Field(..., ge=0, le=1)
    department: Department
    visit_type: VisitType
    doctor_id: int = Field(..., ge=1)
    length_of_stay_hours: float = Field(..., ge=0)
    patient_prior_visit_count: int = Field(..., ge=0)
    patient_prior_avg_los_hours: float = Field(..., ge=0)
    patient_prior_avg_los_missing_flag: int = Field(..., ge=0, le=1)
    registration_date: datetime
    visit_date: datetime

    @computed_field
    @property
    def age_band(self) -> str:
        if self.age <= 17:
            return "0-17"
        if self.age <= 35:
            return "18-35"
        if self.age <= 50:
            return "36-50"
        if self.age <= 65:
            return "51-65"
        return "66+"

    @computed_field
    @property
    def days_since_registration(self) -> int:
        return (self.visit_date.date() - self.registration_date.date()).days

    @computed_field
    @property
    def visit_before_registration_flag(self) -> int:
        return int(self.days_since_registration < 0)

    @computed_field
    @property
    def visit_month(self) -> int:
        return self.visit_date.month

    @computed_field
    @property
    def visit_quarter(self) -> int:
        return ((self.visit_date.month - 1) // 3) + 1

    @computed_field
    @property
    def visit_day_of_week(self) -> int:
        return self.visit_date.weekday()

    @computed_field
    @property
    def visit_week_of_year(self) -> int:
        return int(self.visit_date.isocalendar().week)

    @computed_field
    @property
    def visit_is_weekend(self) -> int:
        return int(self.visit_day_of_week in (5, 6))


class RiskPredictionRequest(BasePredictionFeatures):
    request_id: str | None = Field(None, max_length=80)


class ClaimPredictionRequest(BasePredictionFeatures):
    request_id: str | None = Field(None, max_length=80)
    bill_id: int | None = Field(None, ge=1)
    billed_amount: float = Field(..., ge=0)
    billing_date: datetime
    provider_prior_claim_count: int = Field(..., ge=0)
    provider_prior_rejection_rate: float = Field(..., ge=0, le=1)
    provider_prior_rejection_missing_flag: int = Field(..., ge=0, le=1)
    high_billed_amount_flag: int = Field(..., ge=0, le=1)
    billed_amount_outlier_flag: int = Field(..., ge=0, le=1)
    length_of_stay_hours_outlier_flag: int = Field(..., ge=0, le=1)

    @computed_field
    @property
    def billing_lag_days(self) -> int:
        return (self.billing_date.date() - self.visit_date.date()).days

    @computed_field
    @property
    def billing_before_visit_flag(self) -> int:
        return int(self.billing_lag_days < 0)

    @computed_field
    @property
    def same_day_billing_flag(self) -> int:
        return int(self.billing_lag_days == 0)

    @computed_field
    @property
    def billing_month(self) -> int:
        return self.billing_date.month

    @computed_field
    @property
    def billing_day_of_week(self) -> int:
        return self.billing_date.weekday()


class PredictionResponse(BaseModel):
    request_id: str
    model_name: Literal["risk", "claim"]
    model_version: str
    prediction: str
    probabilities: dict[str, float]
    feature_hash: str
    logged: bool
    generated_at_utc: datetime


class BatchPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_requests: list[RiskPredictionRequest] = Field(default_factory=list, max_length=100)
    claim_requests: list[ClaimPredictionRequest] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def require_at_least_one_request(self) -> "BatchPredictionRequest":
        if not self.risk_requests and not self.claim_requests:
            raise ValueError("Provide at least one risk or claim request")
        return self


class BatchPredictionResponse(BaseModel):
    risk_predictions: list[PredictionResponse]
    claim_predictions: list[PredictionResponse]
    generated_at_utc: datetime


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

