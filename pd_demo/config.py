"""Shared config for Lendistry PD demo — feature allowlist + leakage blocklist."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
DATA_CSV = ARTIFACTS / "sample_data.csv"
MODEL_PATH = ARTIFACTS / "model.joblib"
METRICS_PATH = ARTIFACTS / "metrics.json"
IMPORTANCE_PATH = ARTIFACTS / "feature_importance.csv"
FEATURES_USED_PATH = ARTIFACTS / "features_used.txt"

TARGET_COL = "is_default"
N_ROWS = 2000
RANDOM_SEED = 42

# Columns that reveal or nearly reveal default / Charged-Off / delinquency.
# Never use these as independent variables.
LEAKAGE_COLUMNS = frozenset(
    {
        # Status / outcome
        "status_code_no",
        "charge_off_start_date",
        "non_accrual_start_date",
        "payoff_date",
        "closed_date",
        "loan_status",
        "derived_status",
        # Delinquency
        "days_past_due",
        "total_past_due_balance",
        "total_current_due_balance",
        "current_late_charge_balance",
        "eff_days_past_due",
        "gl_days_past_due",
        "late_charges_balance",
        # Default-interest / collections
        "default_interest_indicator",
        "default_def_interest_indicator",
        "current_def_interest_balance",
        "current_def_interest_rate",
        "current_def_perdiem",
        "starting_def_interest_rate",
        "starting_year_def_int_rate",
        "compound_def_interest_balance",
        "compound_def_int_indicator",
        "collection_officer_no",
        # IDs / PII
        "acctrefno",
        "cifno",
        "tin",
        "tin_hash",
        "name",
        "loan_number",
        "shortname",
        "borrower_loan_nickname",
        "password",
        "signonid",
    }
)

# Safe schema-aligned feature columns (loanacct + cdfi style).
FEATURE_COLUMNS = [
    # Borrower / CDFI financial
    "creditscore",
    "annualgrossrevenue",
    "grossrevattimeofinv",
    "naicscode",
    "entitystructure",
    "investeetype",
    "bankedatintake",
    "jobstimeofinvestment",
    "business_age_years",
    # Loan terms (loanacct)
    "original_note_amount",
    "current_interest_rate",
    "starting_interest_rate",
    "loan_type",
    "portfolio_code_id",
    "loan_group_no",
    "entity",
    "risk_rating_no",
    "loan_age_months",
    "times_renewed",
    "times_extended",
    "current_principal_balance",
    "current_payoff_balance",
    "contractualjurisdiction",
]

CATEGORICAL_FEATURES = [
    "entity",
    "contractualjurisdiction",
    "loan_type",
    "portfolio_code_id",
    "loan_group_no",
    "entitystructure",
    "investeetype",
    "bankedatintake",
    "naicscode",
]

NUMERIC_FEATURES = [c for c in FEATURE_COLUMNS if c not in CATEGORICAL_FEATURES]


def assert_no_leakage(columns) -> None:
    """Raise if any leakage or target column appears in feature set."""
    cols = set(columns)
    bad = cols & LEAKAGE_COLUMNS
    if bad:
        raise AssertionError(f"Leakage columns present in features: {sorted(bad)}")
    if TARGET_COL in cols:
        raise AssertionError(f"Target column '{TARGET_COL}' must not be in X features")
