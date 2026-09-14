"""Generate schema-aligned synthetic loan data with balanced is_default target."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    ARTIFACTS,
    DATA_CSV,
    FEATURE_COLUMNS,
    LEAKAGE_COLUMNS,
    N_ROWS,
    RANDOM_SEED,
    TARGET_COL,
    assert_no_leakage,
)

ENTITIES = ["LLC", "Corp", "Partnership", "Sole Proprietor"]
STATES = ["CA", "TX", "NY", "FL", "IL", "AZ", "GA", "WA", "NC", "OH"]
NAICS = [445110, 484110, 541511, 722511, 236220, 621111, 531210, 238210]


def _generate_row(rng: np.random.Generator, is_default: int) -> dict:
    """Plant a realistic PD signal without using leakage columns.

    Distributions overlap on purpose so the classifier is strong but not perfect.
    """
    # Defaults tend to have weaker credit, thinner revenue, higher rates, worse risk.
    if is_default:
        creditscore = int(rng.normal(600, 55))
        annual_rev = float(rng.lognormal(13.4, 0.6))
        rate = float(rng.normal(12.5, 3.5))
        risk = int(np.clip(rng.normal(6.5, 1.8), 1, 9))
        note = float(rng.lognormal(11.9, 0.5))
        times_ext = int(np.clip(rng.normal(2.2, 1.2), 0, 6))
        times_ren = int(np.clip(rng.normal(1.5, 1.1), 0, 5))
        banked = int(rng.choice([0, 1], p=[0.58, 0.42]))
        jobs = int(max(0, rng.normal(10, 7)))
    else:
        creditscore = int(rng.normal(680, 55))
        annual_rev = float(rng.lognormal(13.9, 0.55))
        rate = float(rng.normal(9.0, 3.0))
        risk = int(np.clip(rng.normal(4.0, 1.8), 1, 9))
        note = float(rng.lognormal(12.0, 0.48))
        times_ext = int(np.clip(rng.normal(1.2, 1.0), 0, 5))
        times_ren = int(np.clip(rng.normal(1.0, 1.0), 0, 4))
        banked = int(rng.choice([0, 1], p=[0.42, 0.58]))
        jobs = int(max(1, rng.normal(16, 8)))
    rate = float(np.clip(rate, 3.5, 24.0))

    creditscore = int(np.clip(creditscore, 500, 850))
    principal = float(np.clip(note * rng.uniform(0.45, 0.95), 5_000, note))
    payoff = float(principal * rng.uniform(0.85, 1.05))
    business_age = float(np.clip(rng.normal(8 if is_default else 12, 5), 0.5, 40))
    loan_age = float(np.clip(rng.normal(28 if is_default else 24, 12), 1, 84))

    return {
        "creditscore": creditscore,
        "annualgrossrevenue": round(annual_rev, 2),
        "grossrevattimeofinv": round(annual_rev * rng.uniform(0.85, 1.25), 2),
        "naicscode": int(rng.choice(NAICS)),
        "entitystructure": int(rng.integers(1, 7)),
        "investeetype": int(rng.integers(1, 6)),
        "bankedatintake": banked,
        "jobstimeofinvestment": jobs,
        "business_age_years": round(business_age, 1),
        "original_note_amount": round(note, 2),
        "current_interest_rate": round(rate, 4),
        "starting_interest_rate": round(rate * rng.uniform(0.9, 1.15), 4),
        "loan_type": int(rng.integers(1, 9)),
        "portfolio_code_id": int(rng.integers(1, 7)),
        "loan_group_no": int(rng.integers(1, 10)),
        "entity": str(rng.choice(ENTITIES)),
        "risk_rating_no": risk,
        "loan_age_months": round(loan_age, 1),
        "times_renewed": times_ren,
        "times_extended": times_ext,
        "current_principal_balance": round(principal, 2),
        "current_payoff_balance": round(payoff, 2),
        "contractualjurisdiction": str(rng.choice(STATES)),
        TARGET_COL: int(is_default),
    }


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)

    n_pos = N_ROWS // 2
    n_neg = N_ROWS - n_pos
    rows = [_generate_row(rng, 1) for _ in range(n_pos)]
    rows += [_generate_row(rng, 0) for _ in range(n_neg)]
    rng.shuffle(rows)

    df = pd.DataFrame(rows)
    # Ensure column order: features then target
    df = df[FEATURE_COLUMNS + [TARGET_COL]]

    # Double-check: no leakage columns generated
    assert_no_leakage(FEATURE_COLUMNS)
    leaked = set(df.columns) & LEAKAGE_COLUMNS
    if leaked:
        raise AssertionError(f"Generated dataset contains leakage columns: {sorted(leaked)}")

    df.to_csv(DATA_CSV, index=False)
    print(f"Wrote {DATA_CSV}")
    print(f"Rows={len(df)}  default_rate={df[TARGET_COL].mean():.3f}")
    print(f"Features ({len(FEATURE_COLUMNS)}): {FEATURE_COLUMNS}")
    print("Leakage columns excluded: OK")


if __name__ == "__main__":
    main()
