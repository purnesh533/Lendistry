"""Business-facing helpers: score applications, risk bands, weekly insights."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from config import (
    ARTIFACTS,
    DATA_CSV,
    FEATURE_COLUMNS,
    IMPORTANCE_PATH,
    MODEL_PATH,
    RANDOM_SEED,
    TARGET_COL,
)

APPLICATIONS_CSV = ARTIFACTS / "applications_scored.csv"
WEEKLY_CSV = ARTIFACTS / "weekly_insights.csv"
DECISIONS_PATH = ARTIFACTS / "decisions.json"

RISK_LOW = "Lower risk"
RISK_MOD = "Moderately risky"
RISK_HIGH = "Risky"

RECOMMENDATIONS = {
    RISK_LOW: "Standard path - approve with usual conditions",
    RISK_MOD: "Request more docs before decision",
    RISK_HIGH: "Refer to senior underwriter",
}

UNDERWRITERS = ["You (demo)", "A. Patel", "J. Chen", "M. Torres"]

BUSINESS_NAMES = [
    "Summit Studio",
    "Coastal Autoworks",
    "Pioneer Boutique",
    "GreenLeaf Catering",
    "Harbor Logistics",
    "BrightPath Clinic",
    "Oak & Iron Construction",
    "Nova Retail Group",
    "Skyline HVAC",
    "Riverbend Farms",
]

# Map model feature names → underwriter-friendly labels
DRIVER_LABELS = {
    "creditscore": "Credit score",
    "risk_rating_no": "Internal risk rating",
    "current_interest_rate": "Interest rate",
    "annualgrossrevenue": "Annual revenue",
    "grossrevattimeofinv": "Revenue at investment",
    "original_note_amount": "Loan amount",
    "current_principal_balance": "Principal balance",
    "business_age_years": "Business age",
    "loan_age_months": "Loan age",
    "times_extended": "Extensions",
    "times_renewed": "Renewals",
    "jobstimeofinvestment": "Jobs at investment",
    "bankedatintake": "Banked at intake",
    "entity": "Entity type",
    "contractualjurisdiction": "Jurisdiction",
    "naicscode": "Industry (NAICS)",
    "entitystructure": "Entity structure",
    "investeetype": "Investee type",
    "loan_type": "Loan type",
    "portfolio_code_id": "Portfolio",
    "loan_group_no": "Loan group",
    "starting_interest_rate": "Starting rate",
    "current_payoff_balance": "Payoff balance",
}


def risk_band(pd_prob: float) -> str:
    if pd_prob < 0.35:
        return RISK_LOW
    if pd_prob < 0.65:
        return RISK_MOD
    return RISK_HIGH


def recommendation_for(band: str) -> str:
    return RECOMMENDATIONS.get(band, RECOMMENDATIONS[RISK_MOD])


def plain_english_risk(pd_prob: float) -> str:
    """Human phrasing for underwriters (not model jargon)."""
    p = float(pd_prob)
    pct = p * 100
    if p <= 0:
        return "Very low chance of default in this demo score."
    if p >= 0.99:
        return "Extremely high chance of default in this demo score."
    # "About 1 in N" where N = round(1/p)
    n = max(2, int(round(1 / p)))
    if p < 0.35:
        return f"About 1 in {n} similar loans would be expected to default ({pct:.0f}% demo risk)."
    if p < 0.65:
        return f"Elevated risk - roughly 1 in {n} similar loans may default ({pct:.0f}% demo risk)."
    return f"High caution - about 1 in {n} similar loans may default ({pct:.0f}% demo risk)."


def load_bundle():
    return joblib.load(MODEL_PATH)


def score_dataframe(df: pd.DataFrame, bundle=None) -> pd.DataFrame:
    bundle = bundle or load_bundle()
    pipe = bundle["pipeline"]
    feats = bundle["feature_columns"]
    X = df[feats].copy()
    proba = pipe.predict_proba(X)[:, 1]
    out = df.copy()
    out["pd_probability"] = proba
    out["risk_band"] = [risk_band(p) for p in proba]
    out["recommendation"] = out["risk_band"].map(RECOMMENDATIONS)
    return out


def why_flagged_row(row: pd.Series, top_n: int = 3) -> str:
    """Simple business explanation from key risk drivers (no leakage fields)."""
    reasons = []
    if row.get("creditscore", 999) < 620:
        reasons.append(f"lower credit score ({int(row['creditscore'])})")
    if row.get("risk_rating_no", 1) >= 6:
        reasons.append(f"weaker internal risk rating ({int(row['risk_rating_no'])})")
    if row.get("current_interest_rate", 0) >= 12:
        reasons.append(f"higher interest rate ({row['current_interest_rate']:.1f}%)")
    if row.get("annualgrossrevenue", 1e9) < 800_000:
        reasons.append("thinner annual revenue")
    if row.get("times_extended", 0) >= 3:
        reasons.append(f"multiple extensions ({int(row['times_extended'])})")
    if row.get("bankedatintake", 1) == 0:
        reasons.append("not banked at intake")
    if row.get("jobstimeofinvestment", 99) <= 6:
        reasons.append("fewer jobs at investment")
    if not reasons:
        reasons.append("combined borrower and loan-term profile")
    return "; ".join(reasons[:top_n])


def load_decisions() -> dict:
    if DECISIONS_PATH.exists():
        return json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    return {}


def save_decisions(data: dict) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    DECISIONS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def set_decision(application_id: str, decision: str, note: str = "") -> dict:
    allowed = {"Approve", "Refer", "Decline", "Pending"}
    if decision not in allowed:
        raise ValueError(f"decision must be one of {sorted(allowed)}")
    data = load_decisions()
    data[application_id] = {
        "decision": decision,
        "note": note,
        "decided_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_decisions(data)
    return data[application_id]


def build_applications(n: int = 40, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Score a sample of synthetic loans as recent applications for underwriters."""
    rng = np.random.default_rng(seed)
    raw = pd.read_csv(DATA_CSV)
    sample = raw.sample(n=min(n, len(raw)), random_state=seed).reset_index(drop=True)
    scored = score_dataframe(sample)

    today = datetime(2026, 9, 11)
    apps = []
    for i, row in scored.iterrows():
        days_ago = int(rng.integers(0, 14))
        app_date = today - timedelta(days=days_ago)
        apps.append(
            {
                "application_id": f"APP-{900100 + i}",
                "business_name": BUSINESS_NAMES[i % len(BUSINESS_NAMES)],
                "application_date": app_date.strftime("%Y-%m-%d"),
                "week_label": "This week" if days_ago < 7 else "Last week",
                "requested_amount": round(float(row["original_note_amount"]), 0),
                "entity": row["entity"],
                "jurisdiction": row["contractualjurisdiction"],
                "credit_score": int(row["creditscore"]),
                "risk_rating": int(row["risk_rating_no"]),
                "interest_rate": round(float(row["current_interest_rate"]), 2),
                "pd_probability": round(float(row["pd_probability"]), 4),
                "risk_band": row["risk_band"],
                "recommendation": row["recommendation"],
                "why_flagged": why_flagged_row(row),
                "plain_english": plain_english_risk(float(row["pd_probability"])),
                "assigned_to": UNDERWRITERS[i % len(UNDERWRITERS)],
                "decision_status": "Pending",
                "actual_default_demo": int(row[TARGET_COL]),
            }
        )
    return pd.DataFrame(apps)


def enrich_with_decisions(apps: pd.DataFrame) -> pd.DataFrame:
    decisions = load_decisions()
    out = apps.copy()
    if "decision_status" not in out.columns:
        out["decision_status"] = "Pending"
    for i, row in out.iterrows():
        d = decisions.get(row["application_id"])
        if d:
            out.at[i, "decision_status"] = d.get("decision", "Pending")
    return out


def build_weekly_summary(apps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for week in ["This week", "Last week"]:
        part = apps[apps["week_label"] == week]
        if part.empty:
            continue
        for band in [RISK_HIGH, RISK_MOD, RISK_LOW]:
            sub = part[part["risk_band"] == band]
            defaults = int(sub["actual_default_demo"].sum()) if len(sub) else 0
            rows.append(
                {
                    "week": week,
                    "risk_band": band,
                    "applications": int(len(sub)),
                    "later_defaulted_demo": defaults,
                    "default_rate_demo": round(defaults / len(sub), 3) if len(sub) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def portfolio_pulse(apps: pd.DataFrame) -> dict:
    """This week vs last week counts by risk band for Home."""
    result = {}
    for week in ["This week", "Last week"]:
        part = apps[apps["week_label"] == week]
        result[week] = {
            "total": int(len(part)),
            "Risky": int((part["risk_band"] == RISK_HIGH).sum()),
            "Moderately risky": int((part["risk_band"] == RISK_MOD).sum()),
            "Lower risk": int((part["risk_band"] == RISK_LOW).sum()),
        }
    return result


def top_drivers(n: int = 8) -> pd.DataFrame:
    imp = pd.read_csv(IMPORTANCE_PATH).head(n).copy()
    imp["feature"] = (
        imp["feature"]
        .str.replace(r"^num__", "", regex=True)
        .str.replace(r"^cat__", "", regex=True)
    )
    imp["label"] = imp["feature"].map(lambda f: DRIVER_LABELS.get(f, f.replace("_", " ").title()))
    return imp.rename(columns={"feature": "driver", "importance": "importance", "label": "label"})


def business_driver_bullets(n: int = 6) -> list[dict]:
    """Underwriter-facing driver list (no raw model % required)."""
    df = top_drivers(n)
    bullets = []
    tips = {
        "Credit score": "Lower scores pull applications toward higher default risk.",
        "Internal risk rating": "Weaker internal ratings are a strong caution signal.",
        "Interest rate": "Higher pricing often accompanies riskier borrower profiles.",
        "Annual revenue": "Thinner revenue leaves less cushion to repay.",
        "Loan amount": "Larger notes increase exposure if the borrower struggles.",
        "Extensions": "Repeated extensions can signal repayment stress.",
        "Business age": "Younger businesses tend to be less stable.",
        "Banked at intake": "Not banked at intake is a relationship/risk flag.",
    }
    for _, row in df.iterrows():
        label = row["label"]
        bullets.append(
            {
                "driver": row["driver"],
                "label": label,
                "importance": float(row["importance"]),
                "tip": tips.get(label, "This factor influences the demo default-risk score."),
            }
        )
    return bullets


def ensure_business_artifacts(force: bool = False) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if force or not APPLICATIONS_CSV.exists() or not WEEKLY_CSV.exists():
        apps = build_applications()
        weekly = build_weekly_summary(apps)
        apps.to_csv(APPLICATIONS_CSV, index=False)
        weekly.to_csv(WEEKLY_CSV, index=False)


if __name__ == "__main__":
    ensure_business_artifacts(force=True)
    print(f"Wrote {APPLICATIONS_CSV}")
    print(f"Wrote {WEEKLY_CSV}")
