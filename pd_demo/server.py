"""FastAPI server for Lendistry PD underwriting demo UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from business_data import (
    APPLICATIONS_CSV,
    RISK_HIGH,
    RISK_LOW,
    RISK_MOD,
    UNDERWRITERS,
    WEEKLY_CSV,
    business_driver_bullets,
    enrich_with_decisions,
    ensure_business_artifacts,
    plain_english_risk,
    portfolio_pulse,
    score_dataframe,
    set_decision,
    top_drivers,
    why_flagged_row,
)
from config import (
    FEATURE_COLUMNS,
    FEATURES_USED_PATH,
    LEAKAGE_COLUMNS,
    METRICS_PATH,
    MODEL_PATH,
)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Lendistry PD Demo", version="2.1")


class ScoreRequest(BaseModel):
    creditscore: int = Field(ge=500, le=850)
    annualgrossrevenue: float
    grossrevattimeofinv: Optional[float] = None
    naicscode: int = 541511
    entitystructure: int = 3
    investeetype: int = 2
    bankedatintake: int = 1
    jobstimeofinvestment: int = 12
    business_age_years: float = 10.0
    original_note_amount: float
    current_interest_rate: float
    starting_interest_rate: Optional[float] = None
    loan_type: int = 3
    portfolio_code_id: int = 2
    loan_group_no: int = 4
    entity: str = "LLC"
    risk_rating_no: int = Field(ge=1, le=9)
    loan_age_months: float = 24.0
    times_renewed: int = 0
    times_extended: int = 0
    current_principal_balance: float
    current_payoff_balance: Optional[float] = None
    contractualjurisdiction: str = "CA"
    threshold: float = 0.5


class DecisionRequest(BaseModel):
    decision: str = Field(description="Approve | Refer | Decline | Pending")
    note: str = ""


@app.on_event("startup")
def _startup() -> None:
    if not MODEL_PATH.exists():
        raise RuntimeError("Missing model.joblib — run generate_data.py and train.py first")
    ensure_business_artifacts(force=False)


def _apps_df() -> pd.DataFrame:
    ensure_business_artifacts(force=False)
    df = pd.read_csv(APPLICATIONS_CSV)
    if "plain_english" not in df.columns:
        df["plain_english"] = df["pd_probability"].map(plain_english_risk)
    if "assigned_to" not in df.columns:
        df["assigned_to"] = [UNDERWRITERS[i % len(UNDERWRITERS)] for i in range(len(df))]
    if "decision_status" not in df.columns:
        df["decision_status"] = "Pending"
    return enrich_with_decisions(df)


def _weekly_df() -> pd.DataFrame:
    ensure_business_artifacts(force=False)
    return pd.read_csv(WEEKLY_CSV)


def _public_app_row(row: dict[str, Any]) -> dict[str, Any]:
    """Strip demo outcome labels from underwriter-facing payloads."""
    out = dict(row)
    out.pop("actual_default_demo", None)
    return out


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/summary")
def summary() -> dict[str, Any]:
    apps = _apps_df()
    return {
        "total": int(len(apps)),
        "risky": int((apps["risk_band"] == RISK_HIGH).sum()),
        "moderate": int((apps["risk_band"] == RISK_MOD).sum()),
        "lower": int((apps["risk_band"] == RISK_LOW).sum()),
        "avg_pd": float(apps["pd_probability"].mean()),
        "pending": int((apps["decision_status"] == "Pending").sum()),
        "pulse": portfolio_pulse(apps),
        "underwriters": UNDERWRITERS,
    }


@app.get("/api/applications")
def applications(
    week: str = Query("All"),
    risk_band_filter: str = Query("All", alias="risk_band"),
    sort_by: str = Query("pd_probability"),
    q: str = Query(""),
    assigned: str = Query("All"),
    decision: str = Query("All"),
) -> list[dict[str, Any]]:
    df = _apps_df()
    if week != "All":
        df = df[df["week_label"] == week]
    if risk_band_filter != "All":
        df = df[df["risk_band"] == risk_band_filter]
    if assigned != "All":
        df = df[df["assigned_to"] == assigned]
    if decision != "All":
        df = df[df["decision_status"] == decision]
    if q.strip():
        needle = q.strip().lower()
        mask = (
            df["application_id"].astype(str).str.lower().str.contains(needle, regex=False)
            | df["business_name"].astype(str).str.lower().str.contains(needle, regex=False)
        )
        df = df[mask]
    ascending = sort_by != "pd_probability"
    if sort_by not in df.columns:
        sort_by = "pd_probability"
    df = df.sort_values(sort_by, ascending=ascending)
    records = json.loads(df.to_json(orient="records"))
    return [_public_app_row(r) for r in records]


@app.get("/api/applications/{application_id}")
def application_detail(application_id: str) -> dict[str, Any]:
    df = _apps_df()
    hit = df[df["application_id"] == application_id]
    if hit.empty:
        raise HTTPException(404, "Application not found")
    return _public_app_row(json.loads(hit.iloc[0].to_json()))


@app.get("/api/applications/{application_id}/summary.txt", response_class=PlainTextResponse)
def application_summary_text(application_id: str) -> str:
    df = _apps_df()
    hit = df[df["application_id"] == application_id]
    if hit.empty:
        raise HTTPException(404, "Application not found")
    a = hit.iloc[0]
    return (
        f"Lendistry underwriting summary (DEMO)\n"
        f"=====================================\n"
        f"Application: {a['application_id']}\n"
        f"Business: {a['business_name']}\n"
        f"Date: {a['application_date']}\n"
        f"Requested: ${float(a['requested_amount']):,.0f}\n"
        f"Assigned to: {a.get('assigned_to', '—')}\n"
        f"Default risk score: {float(a['pd_probability']) * 100:.1f}%\n"
        f"Risk band: {a['risk_band']}\n"
        f"Recommendation: {a['recommendation']}\n"
        f"Decision: {a.get('decision_status', 'Pending')}\n"
        f"Plain English: {a.get('plain_english', plain_english_risk(float(a['pd_probability'])))}\n"
        f"Why flagged: {a['why_flagged']}\n"
        f"Credit score: {a['credit_score']} | Risk rating: {a['risk_rating']} | "
        f"Rate: {float(a['interest_rate']):.1f}%\n"
        f"Entity/State: {a['entity']} / {a['jurisdiction']}\n"
        f"\nNote: Synthetic demo data. Charged-Off proxy for default. Not production risk.\n"
    )


@app.post("/api/applications/{application_id}/decision")
def application_decision(application_id: str, body: DecisionRequest) -> dict[str, Any]:
    df = _apps_df()
    if df[df["application_id"] == application_id].empty:
        raise HTTPException(404, "Application not found")
    try:
        saved = set_decision(application_id, body.decision, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"application_id": application_id, **saved}


@app.get("/api/insights/weekly")
def weekly_insights() -> list[dict[str, Any]]:
    return json.loads(_weekly_df().to_json(orient="records"))


@app.get("/api/insights/outcomes")
def outcomes() -> list[dict[str, Any]]:
    apps = _apps_df()
    # Outcomes use demo labels for manager view only (not in app popup)
    raw = pd.read_csv(APPLICATIONS_CSV)
    out = (
        raw.groupby("risk_band")
        .agg(applications=("application_id", "count"), defaulted=("actual_default_demo", "sum"))
        .reset_index()
    )
    out["default_rate"] = (out["defaulted"] / out["applications"]).round(3)
    return json.loads(out.to_json(orient="records"))


@app.get("/api/insights/drivers")
def drivers() -> list[dict[str, Any]]:
    return business_driver_bullets(8)


@app.get("/api/admin/metrics")
def admin_metrics() -> dict[str, Any]:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@app.get("/api/admin/features")
def admin_features() -> dict[str, Any]:
    text = FEATURES_USED_PATH.read_text(encoding="utf-8") if FEATURES_USED_PATH.exists() else ""
    return {
        "features_used_text": text,
        "leakage_blocklist_size": len(LEAKAGE_COLUMNS),
        "feature_columns": FEATURE_COLUMNS,
        "model_drivers": json.loads(top_drivers(12).to_json(orient="records")),
    }


@app.post("/api/score")
def score_loan(body: ScoreRequest) -> dict[str, Any]:
    payload = body.model_dump()
    threshold = float(payload.pop("threshold", 0.5))
    if payload.get("grossrevattimeofinv") is None:
        payload["grossrevattimeofinv"] = payload["annualgrossrevenue"] * 1.05
    if payload.get("starting_interest_rate") is None:
        payload["starting_interest_rate"] = payload["current_interest_rate"] * 1.05
    if payload.get("current_payoff_balance") is None:
        payload["current_payoff_balance"] = payload["current_principal_balance"] * 0.98

    row = pd.DataFrame([payload])
    for col in FEATURE_COLUMNS:
        if col not in row.columns:
            raise HTTPException(400, f"Missing feature: {col}")
    scored = score_dataframe(row)
    r = scored.iloc[0]
    pd_prob = float(r["pd_probability"])
    band = str(r["risk_band"])
    return {
        "pd_probability": pd_prob,
        "risk_band": band,
        "recommendation": str(r["recommendation"]),
        "why_flagged": why_flagged_row(r),
        "plain_english_risk": plain_english_risk(pd_prob),
        "threshold": threshold,
        "predicted_default": bool(pd_prob >= threshold),
        "plain_english": (
            "Likely will not repay (default risk)"
            if pd_prob >= threshold
            else "Likely will repay (performing)"
        ),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
