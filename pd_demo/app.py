"""Lendistry PD demo — business underwriter UI + admin model lab."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from business_data import (
    APPLICATIONS_CSV,
    RISK_HIGH,
    RISK_LOW,
    RISK_MOD,
    WEEKLY_CSV,
    ensure_business_artifacts,
    top_drivers,
)
from config import (
    DATA_CSV,
    FEATURES_USED_PATH,
    IMPORTANCE_PATH,
    LEAKAGE_COLUMNS,
    METRICS_PATH,
    MODEL_PATH,
    TARGET_COL,
)

st.set_page_config(
    page_title="Lendistry AI Demo | Underwriting",
    page_icon=None,
    layout="wide",
)

BRIGHT_CSS = """
<style>
    .stApp { background: linear-gradient(180deg, #f4f7f6 0%, #e8eef0 100%); color: #1a2b2f; }
    [data-testid="stSidebar"] { background: #f0f5f4 !important; border-right: 1px solid #d5e0e2; }
    [data-testid="stSidebar"] * { color: #1a2b2f; }
    .block-container { padding-top: 1.1rem; }
    .lend-hero {
        background: linear-gradient(120deg, #0f3d4c 0%, #1a5f6e 55%, #2d7a6f 100%);
        color: #f7faf9; padding: 1.2rem 1.4rem; border-radius: 12px; margin-bottom: 1rem;
    }
    .lend-hero h1 { margin: 0 0 0.3rem 0; font-size: 1.65rem; color: #fff !important; }
    .lend-hero p { margin: 0; opacity: 0.92; color: #f7faf9 !important; }
    .pill {
        display: inline-block; background: rgba(255,255,255,0.15);
        padding: 0.2rem 0.65rem; border-radius: 999px; margin-right: 0.35rem;
        font-size: 0.82rem; color: #fff !important;
    }
    .kpi {
        background: #fff; border: 1px solid #d5e0e2; border-radius: 10px;
        padding: 0.85rem 1rem; margin-bottom: 0.5rem;
    }
    .kpi .label { font-size: 0.85rem; color: #5a6b70; }
    .kpi .value { font-size: 1.6rem; font-weight: 700; color: #0f3d4c; }
    .result-good {
        background: #e8f6ef; border-left: 5px solid #1f7a4d; color: #143528;
        padding: 0.9rem 1rem; border-radius: 8px;
    }
    .result-bad {
        background: #fdeeee; border-left: 5px solid #b33a3a; color: #4a1a1a;
        padding: 0.9rem 1rem; border-radius: 8px;
    }
    .result-mid {
        background: #fff7e8; border-left: 5px solid #c48a1a; color: #4a3508;
        padding: 0.9rem 1rem; border-radius: 8px;
    }
</style>
"""

NIGHT_CSS = """
<style>
    .stApp { background: linear-gradient(180deg, #0b1418 0%, #122026 100%); color: #e6eef0; }
    [data-testid="stSidebar"] { background: #0d171c !important; border-right: 1px solid #24343a; }
    [data-testid="stSidebar"] * { color: #d7e4e7 !important; }
    .block-container { padding-top: 1.1rem; }
    .lend-hero {
        background: linear-gradient(120deg, #0a2a33 0%, #123c48 50%, #1a4f4a 100%);
        color: #eef6f5; padding: 1.2rem 1.4rem; border-radius: 12px; margin-bottom: 1rem;
        border: 1px solid #2a4a52;
    }
    .lend-hero h1 { margin: 0 0 0.3rem 0; font-size: 1.65rem; color: #fff !important; }
    .lend-hero p { margin: 0; opacity: 0.92; color: #dceae8 !important; }
    .pill {
        display: inline-block; background: rgba(255,255,255,0.12);
        padding: 0.2rem 0.65rem; border-radius: 999px; margin-right: 0.35rem;
        font-size: 0.82rem; color: #eef6f5 !important;
    }
    .kpi {
        background: #152228; border: 1px solid #2a4a52; border-radius: 10px;
        padding: 0.85rem 1rem; margin-bottom: 0.5rem;
    }
    .kpi .label { font-size: 0.85rem; color: #9bb0b6; }
    .kpi .value { font-size: 1.6rem; font-weight: 700; color: #e6eef0; }
    .result-good { background: #143528; border-left: 5px solid #3ecf8e; color: #d8f5e7; padding: 0.9rem 1rem; border-radius: 8px; }
    .result-bad { background: #3a1a1a; border-left: 5px solid #e06b6b; color: #f8dede; padding: 0.9rem 1rem; border-radius: 8px; }
    .result-mid { background: #3a2e14; border-left: 5px solid #e0b35a; color: #f8ecd0; padding: 0.9rem 1rem; border-radius: 8px; }
    h1, h2, h3, .stMarkdown, .stCaption, label, p { color: #e6eef0 !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #e6eef0 !important; }
    .stButton > button { background: #1a5f6e !important; color: #fff !important; border: 1px solid #2d7a6f !important; }
</style>
"""

LOW_RISK_PRESET = {
    "creditscore": 740,
    "annualgrossrevenue": 2_800_000.0,
    "original_note_amount": 180_000.0,
    "current_interest_rate": 6.5,
    "risk_rating_no": 2,
    "loan_age_months": 18.0,
    "business_age_years": 14.0,
    "times_renewed": 0,
    "times_extended": 0,
    "entity": "LLC",
    "contractualjurisdiction": "CA",
    "loan_type": 3,
    "portfolio_code_id": 2,
    "loan_group_no": 4,
    "entitystructure": 3,
    "investeetype": 2,
    "bankedatintake": 1,
    "naicscode": 541511,
    "jobstimeofinvestment": 22,
    "current_principal_balance": 120_000.0,
}

HIGH_RISK_PRESET = {
    "creditscore": 545,
    "annualgrossrevenue": 420_000.0,
    "original_note_amount": 320_000.0,
    "current_interest_rate": 16.5,
    "risk_rating_no": 8,
    "loan_age_months": 36.0,
    "business_age_years": 4.0,
    "times_renewed": 3,
    "times_extended": 4,
    "entity": "Sole Proprietor",
    "contractualjurisdiction": "FL",
    "loan_type": 6,
    "portfolio_code_id": 5,
    "loan_group_no": 8,
    "entitystructure": 1,
    "investeetype": 4,
    "bankedatintake": 0,
    "naicscode": 722511,
    "jobstimeofinvestment": 4,
    "current_principal_balance": 290_000.0,
}


def apply_theme(mode: str) -> None:
    st.markdown(NIGHT_CSS if mode == "Night mode" else BRIGHT_CSS, unsafe_allow_html=True)


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_metrics():
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_importance():
    return pd.read_csv(IMPORTANCE_PATH)


@st.cache_data
def load_applications():
    ensure_business_artifacts(force=False)
    return pd.read_csv(APPLICATIONS_CSV)


@st.cache_data
def load_weekly():
    ensure_business_artifacts(force=False)
    return pd.read_csv(WEEKLY_CSV)


def require_artifacts() -> bool:
    missing = [p for p in (MODEL_PATH, METRICS_PATH, IMPORTANCE_PATH, DATA_CSV) if not Path(p).exists()]
    if missing:
        st.error("Model artifacts missing. Run `python generate_data.py` then `python train.py`.")
        return False
    ensure_business_artifacts(force=False)
    return True


def kpi_card(label: str, value: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


# ---------- Underwriter pages ----------

def page_underwriter_home():
    st.markdown(
        """
<div class="lend-hero">
  <h1>Underwriting workspace</h1>
  <p>Review loan applications by predicted default risk — built for business users, not data scientists.</p>
  <p style="margin-top:0.6rem">
    <span class="pill">Application queue</span>
    <span class="pill">Business insights</span>
    <span class="pill">PD model underneath</span>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info(
        "Demo uses **synthetic** schema-aligned data. Risk bands come from Probability of Default "
        "(Charged-Off proxy). Use the left menu to open the queue or weekly insights."
    )
    apps = load_applications()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Applications (2 weeks)", str(len(apps)))
    with c2:
        kpi_card("Risky", str(int((apps["risk_band"] == RISK_HIGH).sum())))
    with c3:
        kpi_card("Moderately risky", str(int((apps["risk_band"] == RISK_MOD).sum())))
    with c4:
        kpi_card("Lower risk", str(int((apps["risk_band"] == RISK_LOW).sum())))


def page_application_dashboard():
    st.header("Application dashboard")
    st.caption("Underwriter queue — each application scored for default risk (will they repay?).")

    apps = load_applications()
    f1, f2, f3 = st.columns(3)
    with f1:
        week = st.selectbox("Period", ["All", "This week", "Last week"])
    with f2:
        band = st.selectbox("Risk band", ["All", RISK_HIGH, RISK_MOD, RISK_LOW])
    with f3:
        sort_by = st.selectbox("Sort by", ["pd_probability", "application_date", "requested_amount"])

    view = apps.copy()
    if week != "All":
        view = view[view["week_label"] == week]
    if band != "All":
        view = view[view["risk_band"] == band]
    view = view.sort_values(sort_by, ascending=(sort_by != "pd_probability"))

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("In view", str(len(view)))
    with c2:
        kpi_card("Avg PD", f"{view['pd_probability'].mean():.0%}" if len(view) else "—")
    with c3:
        kpi_card("High risk in view", str(int((view["risk_band"] == RISK_HIGH).sum())))

    show_cols = [
        "application_id",
        "business_name",
        "application_date",
        "week_label",
        "requested_amount",
        "entity",
        "credit_score",
        "pd_probability",
        "risk_band",
        "recommendation",
        "why_flagged",
    ]
    st.dataframe(
        view[show_cols].rename(
            columns={
                "application_id": "Application",
                "business_name": "Business",
                "application_date": "Date",
                "week_label": "Week",
                "requested_amount": "Requested $",
                "entity": "Entity",
                "credit_score": "Credit score",
                "pd_probability": "PD",
                "risk_band": "Risk",
                "recommendation": "Action",
                "why_flagged": "Why flagged",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Inspect one application")
    if len(view):
        pick = st.selectbox("Application ID", view["application_id"].tolist())
        row = view[view["application_id"] == pick].iloc[0]
        css = (
            "result-bad"
            if row["risk_band"] == RISK_HIGH
            else ("result-mid" if row["risk_band"] == RISK_MOD else "result-good")
        )
        st.markdown(
            f'<div class="{css}"><b>{row["business_name"]}</b> ({row["application_id"]})<br/>'
            f'PD = <b>{row["pd_probability"]:.1%}</b> · {row["risk_band"]}<br/>'
            f'{row["recommendation"]}<br/><i>Why: {row["why_flagged"]}</i></div>',
            unsafe_allow_html=True,
        )
        st.progress(float(min(max(row["pd_probability"], 0), 1)))


def page_business_insights():
    st.header("Business insights")
    st.caption("Weekly risk mix and outcomes — what an underwriting manager cares about.")

    apps = load_applications()
    weekly = load_weekly()

    st.subheader("Applications by risk band")
    pivot = (
        weekly.pivot_table(index="week", columns="risk_band", values="applications", fill_value=0)
        .reindex(columns=[RISK_HIGH, RISK_MOD, RISK_LOW])
    )
    st.bar_chart(pivot)
    st.dataframe(weekly, width="stretch", hide_index=True)

    st.subheader("Did risky flags become defaults? (demo outcome)")
    st.write(
        "Using the demo’s known Charged-Off label as a stand-in for later delinquency — "
        "so business users see risk → outcome, not just model metrics."
    )
    outcome = (
        apps.groupby("risk_band")
        .agg(
            applications=("application_id", "count"),
            defaulted=("actual_default_demo", "sum"),
        )
        .reset_index()
    )
    outcome["default_rate"] = (outcome["defaulted"] / outcome["applications"]).round(3)
    st.dataframe(outcome, width="stretch", hide_index=True)
    st.bar_chart(outcome.set_index("risk_band")["default_rate"])

    st.subheader("What drives risk flags")
    drivers = top_drivers(8)
    st.bar_chart(drivers.set_index("driver")["importance"])
    st.caption("Top model drivers (credit score, risk rating, rates, revenue, etc.) — no status/DPD leakage.")

    st.subheader("Recent high-risk examples")
    risky = apps[apps["risk_band"] == RISK_HIGH].head(8)[
        ["application_id", "business_name", "pd_probability", "why_flagged", "recommendation"]
    ]
    st.dataframe(risky, width="stretch", hide_index=True)


# ---------- Admin pages (existing model lab) ----------

def page_admin_overview():
    st.markdown(
        """
<div class="lend-hero">
  <h1>Admin — model lab</h1>
  <p>Technical view: model choice, metrics, calibration health, and sandbox scoring.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    metrics = load_metrics()
    st.success(
        f"Selected model: **{metrics.get('best_model')}** · "
        f"Accuracy **{metrics['accuracy']:.1%}** · AUC **{metrics['roc_auc']:.3f}**"
    )
    with st.expander("Leakage / feature policy"):
        st.write(f"Blocklist size: {len(LEAKAGE_COLUMNS)}")
        if FEATURES_USED_PATH.exists():
            st.code(FEATURES_USED_PATH.read_text(encoding="utf-8"))


def page_admin_performance():
    st.header("Model performance")
    metrics = load_metrics()
    best = metrics.get("best_model", "Unknown")
    if metrics.get("model_comparison"):
        cmp_df = pd.DataFrame(metrics["model_comparison"]).sort_values("roc_auc", ascending=False)
        cmp_df["selected"] = cmp_df["model"].eq(best).map({True: "BEST", False: ""})
        st.dataframe(cmp_df, width="stretch", hide_index=True)
        st.bar_chart(cmp_df.set_index("model")[["roc_auc", "accuracy"]])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{metrics['accuracy']:.1%}")
    c2.metric("ROC AUC", f"{metrics['roc_auc']:.3f}")
    c3.metric("Precision", f"{metrics['precision']:.1%}")
    c4.metric("Recall", f"{metrics['recall']:.1%}")

    cm = metrics["confusion_matrix"]
    chart_df = pd.DataFrame(
        {
            "Bucket": [
                "Actual performing → pred performing",
                "Actual performing → pred default",
                "Actual default → pred performing",
                "Actual default → pred default",
            ],
            "Count": [cm[0][0], cm[0][1], cm[1][0], cm[1][1]],
        }
    )
    st.bar_chart(chart_df.set_index("Bucket"))
    st.caption(f"Train/test 75/25 · n_test={metrics['n_test']} · calibration check via confusion + AUC")


def page_admin_importance():
    st.header("Feature importance")
    imp = load_importance().head(15).copy()
    imp["feature"] = (
        imp["feature"].str.replace(r"^num__", "", regex=True).str.replace(r"^cat__", "", regex=True)
    )
    st.bar_chart(imp.set_index("feature")["importance"])
    st.dataframe(imp, width="stretch", hide_index=True)


def _push_preset_to_widget_keys(preset: dict) -> None:
    st.session_state["w_creditscore"] = int(preset["creditscore"])
    st.session_state["w_rev"] = float(preset["annualgrossrevenue"])
    st.session_state["w_note"] = float(preset["original_note_amount"])
    st.session_state["w_rate"] = float(preset["current_interest_rate"])
    st.session_state["w_risk"] = int(preset["risk_rating_no"])
    st.session_state["w_loan_age"] = float(preset["loan_age_months"])
    st.session_state["w_biz_age"] = float(preset["business_age_years"])
    st.session_state["w_ren"] = int(preset["times_renewed"])
    st.session_state["w_ext"] = int(preset["times_extended"])
    st.session_state["w_entity"] = str(preset["entity"])
    st.session_state["w_state"] = str(preset["contractualjurisdiction"])
    st.session_state["w_ltype"] = int(preset["loan_type"])
    st.session_state["w_port"] = int(preset["portfolio_code_id"])
    st.session_state["w_grp"] = int(preset["loan_group_no"])
    st.session_state["w_estr"] = int(preset["entitystructure"])
    st.session_state["w_inv"] = int(preset["investeetype"])
    st.session_state["w_banked"] = int(preset["bankedatintake"])
    st.session_state["w_naics"] = int(preset["naicscode"])
    st.session_state["w_jobs"] = int(preset["jobstimeofinvestment"])
    st.session_state["w_prin"] = float(preset["current_principal_balance"])


def page_admin_score():
    st.header("Sandbox score a loan")
    st.caption("Admin lab tool — same model used by the underwriting queue.")

    if "pending_preset" in st.session_state:
        _push_preset_to_widget_keys(st.session_state.pop("pending_preset"))
    if "w_creditscore" not in st.session_state:
        _push_preset_to_widget_keys(LOW_RISK_PRESET)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Load low-risk example", use_container_width=True):
            st.session_state.pending_preset = dict(LOW_RISK_PRESET)
            st.rerun()
    with b2:
        if st.button("Load high-risk example", use_container_width=True):
            st.session_state.pending_preset = dict(HIGH_RISK_PRESET)
            st.rerun()

    threshold = st.slider("Decision threshold", 0.10, 0.90, 0.50, 0.05, key="w_threshold")
    col_a, col_b = st.columns(2)
    with col_a:
        creditscore = st.slider("Credit score", 500, 850, key="w_creditscore")
        annualgrossrevenue = st.number_input(
            "Annual gross revenue", 50_000.0, 10_000_000.0, step=10_000.0, key="w_rev"
        )
        original_note_amount = st.number_input(
            "Original note amount", 10_000.0, 2_000_000.0, step=5_000.0, key="w_note"
        )
        current_interest_rate = st.slider("Interest rate (%)", 3.0, 25.0, key="w_rate")
        risk_rating_no = st.slider("Risk rating", 1, 9, key="w_risk")
        loan_age_months = st.slider("Loan age (months)", 1.0, 84.0, key="w_loan_age")
        business_age_years = st.slider("Business age (years)", 0.5, 40.0, key="w_biz_age")
        times_renewed = st.number_input("Times renewed", 0, 10, key="w_ren")
        times_extended = st.number_input("Times extended", 0, 10, key="w_ext")
    with col_b:
        entity = st.selectbox("Entity", ["LLC", "Corp", "Partnership", "Sole Proprietor"], key="w_entity")
        contractualjurisdiction = st.selectbox(
            "Jurisdiction", ["CA", "TX", "NY", "FL", "IL", "AZ", "GA", "WA", "NC", "OH"], key="w_state"
        )
        loan_type = st.selectbox("Loan type", list(range(1, 9)), key="w_ltype")
        portfolio_code_id = st.selectbox("Portfolio", list(range(1, 7)), key="w_port")
        loan_group_no = st.selectbox("Loan group", list(range(1, 10)), key="w_grp")
        entitystructure = st.selectbox("Entity structure", list(range(1, 7)), key="w_estr")
        investeetype = st.selectbox("Investee type", list(range(1, 6)), key="w_inv")
        bankedatintake = st.selectbox("Banked at intake", [0, 1], key="w_banked")
        naicscode = st.selectbox(
            "NAICS", [445110, 484110, 541511, 722511, 236220, 621111, 531210, 238210], key="w_naics"
        )
        jobstimeofinvestment = st.number_input("Jobs", 0, 200, key="w_jobs")
        current_principal_balance = st.number_input(
            "Principal balance", 5_000.0, 2_000_000.0, step=5_000.0, key="w_prin"
        )

    row = {
        "creditscore": int(creditscore),
        "annualgrossrevenue": float(annualgrossrevenue),
        "grossrevattimeofinv": float(annualgrossrevenue) * 1.05,
        "naicscode": int(naicscode),
        "entitystructure": int(entitystructure),
        "investeetype": int(investeetype),
        "bankedatintake": int(bankedatintake),
        "jobstimeofinvestment": int(jobstimeofinvestment),
        "business_age_years": float(business_age_years),
        "original_note_amount": float(original_note_amount),
        "current_interest_rate": float(current_interest_rate),
        "starting_interest_rate": float(current_interest_rate) * 1.05,
        "loan_type": int(loan_type),
        "portfolio_code_id": int(portfolio_code_id),
        "loan_group_no": int(loan_group_no),
        "entity": str(entity),
        "risk_rating_no": int(risk_rating_no),
        "loan_age_months": float(loan_age_months),
        "times_renewed": int(times_renewed),
        "times_extended": int(times_extended),
        "current_principal_balance": float(current_principal_balance),
        "current_payoff_balance": float(current_principal_balance) * 0.98,
        "contractualjurisdiction": str(contractualjurisdiction),
    }

    if st.button("Predict PD", type="primary"):
        bundle = load_model()
        X = pd.DataFrame([row])[bundle["feature_columns"]]
        pd_prob = float(bundle["pipeline"].predict_proba(X)[0, 1])
        flagged = pd_prob >= threshold
        css = "result-bad" if flagged else "result-good"
        msg = "Likely will not repay" if flagged else "Likely will repay"
        st.markdown(
            f'<div class="{css}"><b>PD = {pd_prob:.1%}</b><br/>{msg}</div>',
            unsafe_allow_html=True,
        )
        st.progress(min(max(pd_prob, 0.0), 1.0))


def login_screen():
    st.markdown(
        """
<div class="lend-hero">
  <h1>Lendistry AI Demo</h1>
  <p>Probability of Default — underwriting &amp; admin views</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.write("Choose a role to enter the demo (no password — presentation login).")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Enter as Underwriter", type="primary", use_container_width=True):
            st.session_state.role = "Underwriter"
            st.rerun()
        st.caption("Business screens: application queue + weekly insights.")
    with c2:
        if st.button("Enter as Admin", use_container_width=True):
            st.session_state.role = "Admin"
            st.rerun()
        st.caption("Technical screens: model metrics, drivers, sandbox scoring.")


def main():
    if "ui_theme" not in st.session_state:
        st.session_state.ui_theme = "Bright mode"
    if "role" not in st.session_state:
        st.session_state.role = None

    st.sidebar.markdown("### Lendistry AI Demo")
    theme = st.sidebar.radio(
        "Display mode",
        ["Bright mode", "Night mode"],
        horizontal=True,
        key="ui_theme",
    )
    apply_theme(theme)

    if not require_artifacts():
        return

    if st.session_state.role is None:
        login_screen()
        return

    st.sidebar.markdown(f"**Role:** {st.session_state.role}")
    if st.sidebar.button("Switch role / logout"):
        st.session_state.role = None
        st.rerun()

    if st.session_state.role == "Underwriter":
        page = st.sidebar.radio(
            "Navigate",
            ["Home", "Application dashboard", "Business insights"],
        )
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            "**Risk bands**\n\n"
            f"- {RISK_HIGH}: PD ≥ 65%\n"
            f"- {RISK_MOD}: 35–65%\n"
            f"- {RISK_LOW}: PD < 35%"
        )
        if page == "Home":
            page_underwriter_home()
        elif page == "Application dashboard":
            page_application_dashboard()
        else:
            page_business_insights()
    else:
        page = st.sidebar.radio(
            "Navigate",
            ["Admin overview", "Model performance", "Feature importance", "Sandbox score"],
        )
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Target `{TARGET_COL}`: 1=default risk, 0=performing")
        if page == "Admin overview":
            page_admin_overview()
        elif page == "Model performance":
            page_admin_performance()
        elif page == "Feature importance":
            page_admin_importance()
        else:
            page_admin_score()


if __name__ == "__main__":
    main()
