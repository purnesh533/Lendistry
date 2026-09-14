"""Train multiple PD classifiers, pick best by ROC AUC, assert no leakage."""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import (
    ARTIFACTS,
    CATEGORICAL_FEATURES,
    DATA_CSV,
    FEATURE_COLUMNS,
    FEATURES_USED_PATH,
    IMPORTANCE_PATH,
    LEAKAGE_COLUMNS,
    METRICS_PATH,
    MODEL_PATH,
    NUMERIC_FEATURES,
    RANDOM_SEED,
    TARGET_COL,
    assert_no_leakage,
)

COMPARISON_PATH = ARTIFACTS / "model_comparison.csv"


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ]
    )


def candidate_models() -> dict:
    return {
        "LogisticRegression": LogisticRegression(
            max_iter=1000,
            random_state=RANDOM_SEED,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.08,
            random_state=RANDOM_SEED,
        ),
    }


def get_feature_names(pipeline: Pipeline) -> list[str]:
    pre: ColumnTransformer = pipeline.named_steps["preprocess"]
    return list(pre.get_feature_names_out())


def extract_importance(pipeline: Pipeline) -> pd.DataFrame:
    model = pipeline.named_steps["model"]
    names = get_feature_names(pipeline)
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = np.abs(model.coef_).ravel()
        # normalize to sum ~1 for display
        total = values.sum()
        values = values / total if total > 0 else values
    else:
        values = np.zeros(len(names))
    return (
        pd.DataFrame({"feature": names, "importance": values})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def evaluate(pipe: Pipeline, X_test, y_test) -> dict:
    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "classification_report": classification_report(
            y_test, pred, target_names=["Active(0)", "ChargedOff(1)"], output_dict=True
        ),
        "proba": proba,
        "pred": pred,
    }


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if not DATA_CSV.exists():
        raise FileNotFoundError(f"Missing {DATA_CSV}. Run generate_data.py first.")

    df = pd.read_csv(DATA_CSV)
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    assert_no_leakage(feature_cols)

    drop_leak = [c for c in df.columns if c in LEAKAGE_COLUMNS]
    if drop_leak:
        raise AssertionError(f"Refusing to train — leakage columns in CSV: {drop_leak}")

    X = df[feature_cols]
    y = df[TARGET_COL].astype(int)
    assert TARGET_COL not in X.columns
    assert_no_leakage(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_SEED, stratify=y
    )

    results = []
    trained = {}
    print("Training candidates...")
    for name, clf in candidate_models().items():
        pipe = Pipeline(
            steps=[
                ("preprocess", build_preprocessor()),
                ("model", clf),
            ]
        )
        pipe.fit(X_train, y_train)
        ev = evaluate(pipe, X_test, y_test)
        trained[name] = (pipe, ev)
        results.append(
            {
                "model": name,
                "accuracy": ev["accuracy"],
                "precision": ev["precision"],
                "recall": ev["recall"],
                "roc_auc": ev["roc_auc"],
            }
        )
        print(
            f"  {name}: accuracy={ev['accuracy']:.3f}  "
            f"AUC={ev['roc_auc']:.3f}  precision={ev['precision']:.3f}  "
            f"recall={ev['recall']:.3f}"
        )

    comparison = pd.DataFrame(results).sort_values("roc_auc", ascending=False)
    comparison.to_csv(COMPARISON_PATH, index=False)

    best_name = comparison.iloc[0]["model"]
    best_pipe, best_ev = trained[best_name]
    print(f"\nBest model by ROC AUC: {best_name}")

    metrics = {
        "best_model": best_name,
        "selection_metric": "roc_auc",
        "accuracy": best_ev["accuracy"],
        "precision": best_ev["precision"],
        "recall": best_ev["recall"],
        "roc_auc": best_ev["roc_auc"],
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "default_rate_train": float(y_train.mean()),
        "default_rate_test": float(y_test.mean()),
        "confusion_matrix": best_ev["confusion_matrix"],
        "classification_report": best_ev["classification_report"],
        "model_comparison": results,
        "leakage_check": "PASSED — no leakage columns in features",
        "features_used": feature_cols,
        "leakage_blocklist_size": len(LEAKAGE_COLUMNS),
    }

    imp_df = extract_importance(best_pipe)

    joblib.dump(
        {
            "pipeline": best_pipe,
            "best_model": best_name,
            "feature_columns": feature_cols,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": TARGET_COL,
            "model_comparison": results,
        },
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    imp_df.to_csv(IMPORTANCE_PATH, index=False)
    FEATURES_USED_PATH.write_text(
        "\n".join(
            [
                "Lendistry PD Demo — features used (leakage-safe)",
                f"Target: {TARGET_COL} (1=Charged-Off / default, 0=Active-like)",
                f"Best model: {best_name} (selected by ROC AUC)",
                "",
                "CANDIDATES COMPARED:",
                *[
                    f"  - {r['model']}: AUC={r['roc_auc']:.4f}, Acc={r['accuracy']:.4f}"
                    for r in sorted(results, key=lambda x: -x["roc_auc"])
                ],
                "",
                "FEATURES:",
                *[f"  - {c}" for c in feature_cols],
                "",
                "LEAKAGE BLOCKLIST (excluded):",
                *[f"  - {c}" for c in sorted(LEAKAGE_COLUMNS)],
            ]
        ),
        encoding="utf-8",
    )

    print("Leakage check: PASSED")
    print(f"Best Accuracy={metrics['accuracy']:.3f}  AUC={metrics['roc_auc']:.3f}")
    print(f"Wrote {MODEL_PATH}")
    print(f"Wrote {METRICS_PATH}")
    print(f"Wrote {COMPARISON_PATH}")
    print(f"Wrote {IMPORTANCE_PATH}")
    print(f"Wrote {FEATURES_USED_PATH}")


if __name__ == "__main__":
    main()
